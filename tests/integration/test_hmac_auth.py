from __future__ import annotations

import json
import time
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from connector.app import create_app
from connector.auth import AuthConfig, AuthValidator
from connector.config import Settings
from connector.security import NonceReplayCache, build_canonical_string, sha256_hex, sign_canonical


class OmegaStub:
    async def scan_attachment(self, payload, *, debug: bool = False):
        return {
            "request_id": payload.request_id,
            "tenant_id": payload.tenant_id,
            "risk_score": 10,
            "verdict": "allow",
            "reasons": ["ok"],
            "evidence_id": "e-hmac",
            "policy_trace": {"off": False, "debug": debug},
        }


def _runtime_hmac() -> SimpleNamespace:
    settings = Settings(
        connector_host="0.0.0.0",
        connector_port=18080,
        connector_api_keys=["test-key"],
        connector_require_hmac=True,
        connector_hmac_secret="test-secret",
        connector_fail_mode="quarantine",
        connector_debug_document_scan=False,
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
        AuthConfig(api_keys=["test-key"], require_hmac=True, hmac_secret="test-secret", max_clock_skew_sec=300),
        replay_cache=NonceReplayCache(ttl_sec=600, max_entries=1000),
    )
    return SimpleNamespace(settings=settings, auth=auth, omega=OmegaStub())


def _signed_headers(path: str, body: bytes, *, tenant_id: str, request_id: str) -> dict[str, str]:
    ts = str(int(time.time()))
    nonce = str(uuid4())
    canonical = build_canonical_string(
        method="POST",
        path=path,
        body_sha256_hex=sha256_hex(body),
        tenant_id=tenant_id,
        request_id=request_id,
        timestamp=ts,
        nonce=nonce,
    )
    signature = sign_canonical(canonical, "test-secret")
    return {
        "Content-Type": "application/json",
        "X-API-Key": "test-key",
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": signature,
    }


@pytest.mark.asyncio
async def test_hmac_valid_signature() -> None:
    app = create_app()
    app.state.runtime = _runtime_hmac()
    payload = {"tenant_id": "tenant-a", "request_id": "hmac-1", "extracted_text": "hello"}
    body = json.dumps(payload).encode("utf-8")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _signed_headers("/v1/scan/attachment", body, tenant_id="tenant-a", request_id="hmac-1")
        response = await client.post("/v1/scan/attachment", content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["verdict"] == "allow"


@pytest.mark.asyncio
async def test_hmac_invalid_signature() -> None:
    app = create_app()
    app.state.runtime = _runtime_hmac()
    payload = {"tenant_id": "tenant-a", "request_id": "hmac-2", "extracted_text": "hello"}
    body = json.dumps(payload).encode("utf-8")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        headers = _signed_headers("/v1/scan/attachment", body, tenant_id="tenant-a", request_id="hmac-2")
        headers["X-Signature"] = "invalid"
        response = await client.post("/v1/scan/attachment", content=body, headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_signature"
