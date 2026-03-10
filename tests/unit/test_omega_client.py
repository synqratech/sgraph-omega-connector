from __future__ import annotations

from collections import deque
from typing import Any

import httpx
import pytest

from connector.models import ScanAttachmentRequest
from connector.omega_client import (
    OmegaCircuitOpen,
    OmegaClient,
    OmegaRejectedError,
    OmegaTimeoutError,
    OmegaUnavailableError,
)


class _AsyncClientStub:
    def __init__(self, queue: deque[Any], **_: Any) -> None:
        self._queue = queue

    async def __aenter__(self) -> "_AsyncClientStub":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[override]
        return False

    async def post(self, *_: Any, **__: Any) -> httpx.Response:
        item = self._queue.popleft()
        if isinstance(item, Exception):
            raise item
        return item


def _response(status: int, body: dict[str, Any]) -> httpx.Response:
    req = httpx.Request("POST", "https://omega.example/v1/scan/attachment")
    return httpx.Response(status_code=status, json=body, request=req)


def _client() -> OmegaClient:
    return OmegaClient(
        base_url="https://omega.example",
        api_key="k",
        require_hmac=False,
        hmac_secret="",
        tls_verify=True,
        ca_cert_path="",
        timeout_ms=100,
        retry_count=1,
        breaker_fails=2,
        breaker_reset_sec=30,
    )


@pytest.mark.asyncio
async def test_omega_client_rejected_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    queue: deque[Any] = deque([_response(400, {"detail": "invalid_file_base64"})])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _AsyncClientStub(queue, **kwargs))
    client = _client()
    payload = ScanAttachmentRequest(tenant_id="tenant-a", request_id="r1", file_base64="!!!")
    with pytest.raises(OmegaRejectedError) as exc_info:
        await client.scan_attachment(payload)
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail_code == "invalid_file_base64"


@pytest.mark.asyncio
async def test_omega_client_rejected_4xx_does_not_open_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    queue: deque[Any] = deque(
        [
            _response(400, {"detail": "invalid_file_base64"}),
            _response(
                200,
                {
                    "request_id": "r1-ok",
                    "tenant_id": "tenant-a",
                    "risk_score": 0,
                    "verdict": "allow",
                    "reasons": [],
                    "evidence_id": "ev-ok",
                    "policy_trace": {},
                },
            ),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _AsyncClientStub(queue, **kwargs))
    client = _client()
    with pytest.raises(OmegaRejectedError):
        await client.scan_attachment(ScanAttachmentRequest(tenant_id="tenant-a", request_id="r1", file_base64="!!!"))
    out = await client.scan_attachment(ScanAttachmentRequest(tenant_id="tenant-a", request_id="r1-ok", extracted_text="hello"))
    assert out["verdict"] == "allow"


@pytest.mark.asyncio
async def test_omega_client_timeout_then_success(monkeypatch: pytest.MonkeyPatch) -> None:
    queue: deque[Any] = deque(
        [
            httpx.TimeoutException("timeout"),
            _response(
                200,
                {
                    "request_id": "r2",
                    "tenant_id": "tenant-a",
                    "risk_score": 0,
                    "verdict": "allow",
                    "reasons": [],
                    "evidence_id": "ev-1",
                    "policy_trace": {},
                },
            ),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _AsyncClientStub(queue, **kwargs))
    client = _client()
    payload = ScanAttachmentRequest(tenant_id="tenant-a", request_id="r2", extracted_text="hello")
    out = await client.scan_attachment(payload)
    assert out["verdict"] == "allow"


@pytest.mark.asyncio
async def test_omega_client_5xx_unavailable_and_circuit(monkeypatch: pytest.MonkeyPatch) -> None:
    queue: deque[Any] = deque(
        [
            _response(500, {"detail": "oops"}),
            _response(500, {"detail": "oops"}),
            _response(500, {"detail": "oops"}),
            _response(500, {"detail": "oops"}),
        ]
    )
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _AsyncClientStub(queue, **kwargs))
    client = _client()
    payload = ScanAttachmentRequest(tenant_id="tenant-a", request_id="r3", extracted_text="hello")

    with pytest.raises(OmegaUnavailableError):
        await client.scan_attachment(payload)
    with pytest.raises(OmegaUnavailableError):
        await client.scan_attachment(payload)
    with pytest.raises(OmegaCircuitOpen):
        await client.scan_attachment(payload)


@pytest.mark.asyncio
async def test_omega_client_timeout_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    queue: deque[Any] = deque([httpx.TimeoutException("timeout"), httpx.TimeoutException("timeout")])
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: _AsyncClientStub(queue, **kwargs))
    client = _client()
    payload = ScanAttachmentRequest(tenant_id="tenant-a", request_id="r4", extracted_text="hello")
    with pytest.raises(OmegaTimeoutError):
        await client.scan_attachment(payload)
