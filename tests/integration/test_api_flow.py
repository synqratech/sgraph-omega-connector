from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from connector.app import create_app
from connector.auth import AuthConfig, AuthValidator
from connector.config import Settings
from connector.omega_client import OmegaRejectedError, OmegaTimeoutError, OmegaUnavailableError
from connector.security import NonceReplayCache


class OmegaStub:
    def __init__(self, mode: str = "ok") -> None:
        self.mode = mode

    async def scan_attachment(self, payload, *, debug: bool = False):
        if self.mode == "timeout":
            raise OmegaTimeoutError("timeout")
        if self.mode == "unavailable":
            raise OmegaUnavailableError("unavailable")
        if self.mode == "rejected":
            raise OmegaRejectedError(status_code=400, detail_code="invalid_file_base64")
        if self.mode == "invalid":
            return {"foo": "bar"}
        return {
            "request_id": payload.request_id,
            "tenant_id": payload.tenant_id,
            "risk_score": 18,
            "verdict": "allow",
            "reasons": ["ok"],
            "evidence_id": "e-1",
            "policy_trace": {"off": False, "debug": debug},
        }


def _runtime(*, omega_mode: str = "ok", debug_enabled: bool = False):
    settings = Settings(
        connector_host="0.0.0.0",
        connector_port=18080,
        connector_api_keys=["test-key"],
        connector_require_hmac=False,
        connector_hmac_secret="",
        connector_fail_mode="quarantine",
        connector_debug_document_scan=debug_enabled,
        log_level="INFO",
        audit_redaction=True,
        nonce_ttl_sec=600,
        max_clock_skew_sec=300,
        omega_base_url="http://omega",
        omega_api_key="k",
        omega_require_hmac=False,
        omega_hmac_secret="",
        omega_tls_verify=False,
        omega_ca_cert_path="",
        omega_timeout_ms=1000,
        omega_retry_count=0,
        omega_circuit_breaker_fails=5,
        omega_circuit_breaker_reset_sec=30,
    )
    auth = AuthValidator(
        AuthConfig(api_keys=["test-key"], require_hmac=False, hmac_secret="", max_clock_skew_sec=300),
        replay_cache=NonceReplayCache(ttl_sec=600, max_entries=1000),
    )
    return SimpleNamespace(settings=settings, auth=auth, omega=OmegaStub(omega_mode))


@pytest.mark.asyncio
async def test_scan_attachment_happy_path() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="ok")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment",
            headers={"X-API-Key": "test-key"},
            json={"tenant_id": "tenant-a", "request_id": "r1", "extracted_text": "hello"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "allow"
    assert body["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_scan_attachment_timeout_fallback() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="timeout")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment",
            headers={"X-API-Key": "test-key"},
            json={"tenant_id": "tenant-a", "request_id": "r2", "extracted_text": "hello"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "quarantine"
    assert "omega_timeout" in body["reasons"]


@pytest.mark.asyncio
async def test_scan_attachment_rejected_4xx_fallback() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="rejected")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment",
            headers={"X-API-Key": "test-key"},
            json={"tenant_id": "tenant-a", "request_id": "r2b", "extracted_text": "hello"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "quarantine"
    assert "omega_rejected_4xx" in body["reasons"]
    assert body["policy_trace"]["upstream_status"] == 400
    assert body["policy_trace"]["upstream_detail_code"] == "invalid_file_base64"


@pytest.mark.asyncio
async def test_scan_attachment_unavailable_fallback() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="unavailable")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment",
            headers={"X-API-Key": "test-key"},
            json={"tenant_id": "tenant-a", "request_id": "r2c", "extracted_text": "hello"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["verdict"] == "quarantine"
    assert "omega_unavailable" in body["reasons"]


@pytest.mark.asyncio
async def test_scan_attachment_rejects_bad_api_key() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="ok")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment",
            headers={"X-API-Key": "wrong-key"},
            json={"tenant_id": "tenant-a", "request_id": "r3", "extracted_text": "hello"},
        )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


@pytest.mark.asyncio
async def test_debug_endpoint_guarded() -> None:
    app = create_app()
    app.state.runtime = _runtime(omega_mode="ok", debug_enabled=False)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/scan/attachment/document_scan_report",
            headers={"X-API-Key": "test-key"},
            json={"tenant_id": "tenant-a", "request_id": "r4", "extracted_text": "hello"},
        )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "forbidden"
