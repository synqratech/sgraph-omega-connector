from __future__ import annotations

import json
import logging
import uuid
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from connector.auth import AuthConfig, AuthValidator
from connector.config import Settings, load_settings
from connector.errors import http_error
from connector.logging_utils import audit_log
from connector.models import ErrorResponse, ScanAttachmentRequest, ScanAttachmentResponse
from connector.omega_client import (
    OmegaCircuitOpen,
    OmegaClient,
    OmegaClientError,
    OmegaRejectedError,
    OmegaTimeoutError,
    OmegaUnavailableError,
)
from connector.security import NonceReplayCache


class ConnectorRuntime:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.replay_cache = NonceReplayCache(ttl_sec=settings.nonce_ttl_sec, max_entries=100000)
        self.auth = AuthValidator(
            AuthConfig(
                api_keys=settings.connector_api_keys,
                require_hmac=settings.connector_require_hmac,
                hmac_secret=settings.connector_hmac_secret,
                max_clock_skew_sec=settings.max_clock_skew_sec,
            ),
            replay_cache=self.replay_cache,
        )
        self.omega = OmegaClient(
            base_url=settings.omega_base_url,
            api_key=settings.omega_api_key,
            require_hmac=settings.omega_require_hmac,
            hmac_secret=settings.omega_hmac_secret,
            tls_verify=settings.omega_tls_verify,
            ca_cert_path=settings.omega_ca_cert_path,
            timeout_ms=settings.omega_timeout_ms,
            retry_count=settings.omega_retry_count,
            breaker_fails=settings.omega_circuit_breaker_fails,
            breaker_reset_sec=settings.omega_circuit_breaker_reset_sec,
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    app.state.runtime = ConnectorRuntime(settings)
    yield


def _normalize_response(raw: dict[str, Any], request_payload: ScanAttachmentRequest) -> ScanAttachmentResponse:
    request_id = str(raw.get("request_id") or request_payload.request_id or str(uuid.uuid4()))
    tenant_id = str(raw.get("tenant_id") or request_payload.tenant_id)
    risk_score = int(raw.get("risk_score", 0))
    risk_score = max(0, min(100, risk_score))
    verdict = str(raw.get("verdict", "quarantine")).strip().lower()
    if verdict not in {"allow", "quarantine", "block"}:
        verdict = "quarantine"

    reasons = [str(item) for item in (raw.get("reasons") or [])]
    evidence_id = str(raw.get("evidence_id") or str(uuid.uuid4()))
    policy_trace = raw.get("policy_trace") if isinstance(raw.get("policy_trace"), dict) else {}
    attestation = raw.get("attestation") if isinstance(raw.get("attestation"), dict) else None
    return ScanAttachmentResponse(
        request_id=request_id,
        tenant_id=tenant_id,
        risk_score=risk_score,
        verdict=verdict,
        reasons=reasons,
        evidence_id=evidence_id,
        policy_trace=policy_trace,
        attestation=attestation,
    )


def _fallback_response(
    *,
    payload: ScanAttachmentRequest,
    reason: str,
    fail_mode: str,
    detail_code: str | None = None,
    upstream_status: int | None = None,
) -> ScanAttachmentResponse:
    request_id = str(payload.request_id or str(uuid.uuid4()))
    verdict = fail_mode if fail_mode in {"allow", "quarantine", "block"} else "quarantine"
    risk = {"allow": 0, "quarantine": 55, "block": 95}.get(verdict, 55)
    policy_trace: dict[str, Any] = {
        "source": "connector_fallback",
        "reason": reason,
        "fail_mode": verdict,
    }
    if detail_code:
        policy_trace["upstream_detail_code"] = detail_code
    if upstream_status is not None:
        policy_trace["upstream_status"] = int(upstream_status)
    return ScanAttachmentResponse(
        request_id=request_id,
        tenant_id=payload.tenant_id,
        risk_score=risk,
        verdict=verdict,
        reasons=[reason],
        evidence_id=str(uuid.uuid4()),
        policy_trace=policy_trace,
    )


def create_app() -> FastAPI:
    app = FastAPI(title="SGraph Omega Connector", version="1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        payload = ErrorResponse(
            request_id=None,
            error={
                "code": "bad_request",
                "message": "request validation failed",
                "details": {"errors": exc.errors()},
            },
        )
        return JSONResponse(status_code=400, content=payload.model_dump())

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: Request, exc: HTTPException):
        detail = exc.detail
        if isinstance(detail, dict) and "error" in detail:
            return JSONResponse(status_code=exc.status_code, content=detail)
        payload = ErrorResponse(
            request_id=None,
            error={
                "code": "http_error",
                "message": str(detail),
                "details": {},
            },
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def fallback_exception_handler(_: Request, exc: Exception):
        if hasattr(exc, "status_code") and hasattr(exc, "detail"):
            detail = exc.detail
            if isinstance(detail, dict) and "error" in detail:
                return JSONResponse(status_code=exc.status_code, content=detail)
        payload = ErrorResponse(
            request_id=None,
            error={
                "code": "internal_error",
                "message": "internal server error",
                "details": {},
            },
        )
        return JSONResponse(status_code=500, content=payload.model_dump())

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/scan/attachment", response_model=ScanAttachmentResponse)
    async def scan_attachment(request: Request) -> ScanAttachmentResponse:
        runtime: ConnectorRuntime = app.state.runtime
        body_bytes = await request.body()
        try:
            body_json = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            raise http_error(400, "bad_request", "invalid JSON payload")

        try:
            payload = ScanAttachmentRequest.model_validate(body_json)
        except ValidationError as exc:
            raise http_error(
                400,
                "bad_request",
                "request validation failed",
                details={"errors": exc.errors(include_url=False, include_context=False)},
            )
        if not payload.request_id:
            payload.request_id = str(uuid.uuid4())

        api_key = runtime.auth.validate_api_key(request.headers.get("X-API-Key"), request_id=payload.request_id)
        runtime.auth.validate_hmac(
            request=request,
            body_bytes=body_bytes,
            payload=payload,
            provided_api_key=api_key,
        )

        try:
            raw = await runtime.omega.scan_attachment(payload, debug=False)
            normalized = _normalize_response(raw, payload)
        except OmegaCircuitOpen:
            normalized = _fallback_response(payload=payload, reason="omega_unavailable", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaTimeoutError:
            normalized = _fallback_response(payload=payload, reason="omega_timeout", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaRejectedError as exc:
            normalized = _fallback_response(
                payload=payload,
                reason="omega_rejected_4xx",
                fail_mode=runtime.settings.connector_fail_mode,
                detail_code=exc.detail_code,
                upstream_status=exc.status_code,
            )
        except OmegaUnavailableError:
            normalized = _fallback_response(payload=payload, reason="omega_unavailable", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaClientError:
            normalized = _fallback_response(payload=payload, reason="invalid_response", fail_mode=runtime.settings.connector_fail_mode)
        except Exception:
            normalized = _fallback_response(payload=payload, reason="invalid_response", fail_mode=runtime.settings.connector_fail_mode)

        audit_log(
            request_id=normalized.request_id,
            tenant_id=normalized.tenant_id,
            verdict=normalized.verdict,
            risk_score=normalized.risk_score,
            reasons=normalized.reasons,
            redact=runtime.settings.audit_redaction,
            extra={"endpoint": "/v1/scan/attachment"},
        )
        return normalized

    @app.post("/v1/scan/attachment/document_scan_report", response_model=ScanAttachmentResponse)
    async def scan_attachment_document_scan_report(request: Request) -> ScanAttachmentResponse:
        runtime: ConnectorRuntime = app.state.runtime
        if not runtime.settings.connector_debug_document_scan:
            raise http_error(403, "forbidden", "debug document scan is disabled")

        body_bytes = await request.body()
        try:
            body_json = json.loads(body_bytes.decode("utf-8"))
        except Exception:
            raise http_error(400, "bad_request", "invalid JSON payload")

        try:
            payload = ScanAttachmentRequest.model_validate(body_json)
        except ValidationError as exc:
            raise http_error(
                400,
                "bad_request",
                "request validation failed",
                details={"errors": exc.errors(include_url=False, include_context=False)},
            )
        if not payload.request_id:
            payload.request_id = str(uuid.uuid4())

        api_key = runtime.auth.validate_api_key(request.headers.get("X-API-Key"), request_id=payload.request_id)
        runtime.auth.validate_hmac(
            request=request,
            body_bytes=body_bytes,
            payload=payload,
            provided_api_key=api_key,
        )

        try:
            raw = await runtime.omega.scan_attachment(payload, debug=True)
            normalized = _normalize_response(raw, payload)
        except OmegaCircuitOpen:
            normalized = _fallback_response(payload=payload, reason="omega_unavailable", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaTimeoutError:
            normalized = _fallback_response(payload=payload, reason="omega_timeout", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaRejectedError as exc:
            normalized = _fallback_response(
                payload=payload,
                reason="omega_rejected_4xx",
                fail_mode=runtime.settings.connector_fail_mode,
                detail_code=exc.detail_code,
                upstream_status=exc.status_code,
            )
        except OmegaUnavailableError:
            normalized = _fallback_response(payload=payload, reason="omega_unavailable", fail_mode=runtime.settings.connector_fail_mode)
        except OmegaClientError:
            normalized = _fallback_response(payload=payload, reason="invalid_response", fail_mode=runtime.settings.connector_fail_mode)
        except Exception:
            normalized = _fallback_response(payload=payload, reason="invalid_response", fail_mode=runtime.settings.connector_fail_mode)

        audit_log(
            request_id=normalized.request_id,
            tenant_id=normalized.tenant_id,
            verdict=normalized.verdict,
            risk_score=normalized.risk_score,
            reasons=normalized.reasons,
            redact=runtime.settings.audit_redaction,
            extra={"endpoint": "/v1/scan/attachment/document_scan_report"},
        )
        return normalized

    return app
