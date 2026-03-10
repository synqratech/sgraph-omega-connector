from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from connector.models import ScanAttachmentRequest
from connector.security import build_canonical_string, sha256_hex, sign_canonical


@dataclass
class CircuitState:
    failure_count: int = 0
    opened_until_ts: float = 0.0


class OmegaClientError(RuntimeError):
    pass


class OmegaCircuitOpen(OmegaClientError):
    pass


class OmegaTimeoutError(OmegaClientError):
    pass


class OmegaUnavailableError(OmegaClientError):
    pass


class OmegaRejectedError(OmegaClientError):
    def __init__(self, *, status_code: int, detail_code: str, response_body: str = "") -> None:
        super().__init__(f"omega upstream rejected request: {status_code}")
        self.status_code = int(status_code)
        self.detail_code = detail_code
        self.response_body = response_body


class OmegaClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        require_hmac: bool,
        hmac_secret: str,
        tls_verify: bool,
        ca_cert_path: str,
        timeout_ms: int,
        retry_count: int,
        breaker_fails: int,
        breaker_reset_sec: int,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.require_hmac = require_hmac
        self.hmac_secret = hmac_secret
        self.tls_verify = bool(tls_verify)
        self.ca_cert_path = str(ca_cert_path or "").strip()
        self.timeout_ms = timeout_ms
        self.retry_count = max(0, retry_count)
        self.breaker_fails = max(1, breaker_fails)
        self.breaker_reset_sec = max(1, breaker_reset_sec)
        self._state = CircuitState()

    def _can_attempt(self) -> bool:
        now = time.time()
        if self._state.opened_until_ts <= now:
            return True
        return False

    def _record_failure(self) -> None:
        self._state.failure_count += 1
        if self._state.failure_count >= self.breaker_fails:
            self._state.opened_until_ts = time.time() + self.breaker_reset_sec

    def _record_success(self) -> None:
        self._state.failure_count = 0
        self._state.opened_until_ts = 0.0

    def _headers(self, *, path: str, body: bytes, tenant_id: str, request_id: str) -> dict[str, str]:
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
        }
        if not self.require_hmac:
            return headers
        ts = str(int(time.time()))
        nonce = str(uuid.uuid4())
        canonical = build_canonical_string(
            method="POST",
            path=path,
            body_sha256_hex=sha256_hex(body),
            tenant_id=tenant_id,
            request_id=request_id,
            timestamp=ts,
            nonce=nonce,
        )
        headers["X-Timestamp"] = ts
        headers["X-Nonce"] = nonce
        headers["X-Signature"] = sign_canonical(canonical, self.hmac_secret)
        return headers

    def _resolve_verify(self) -> bool | str:
        if not self.tls_verify:
            return False
        if self.ca_cert_path:
            return self.ca_cert_path
        return True

    @staticmethod
    def _detail_code(response: httpx.Response) -> str:
        try:
            data = response.json()
            if isinstance(data, dict):
                value = data.get("detail")
                if isinstance(value, str) and value.strip():
                    return value.strip()
        except Exception:
            pass
        text = response.text.strip()
        if not text:
            return f"http_{response.status_code}"
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                value = parsed.get("detail")
                if isinstance(value, str) and value.strip():
                    return value.strip()
        except Exception:
            pass
        return f"http_{response.status_code}"

    async def scan_attachment(self, payload: ScanAttachmentRequest, *, debug: bool = False) -> dict[str, Any]:
        if not self._can_attempt():
            raise OmegaCircuitOpen("omega circuit breaker is open")

        path = "/v1/scan/attachment/document_scan_report" if debug else "/v1/scan/attachment"
        url = f"{self.base_url}{path}"
        body_json = payload.model_dump(mode="json", exclude_none=True)
        body = httpx.Request("POST", url, json=body_json).content
        headers = self._headers(
            path=path,
            body=body,
            tenant_id=payload.tenant_id,
            request_id=str(payload.request_id or ""),
        )

        last_error: OmegaClientError | None = None
        timeout = httpx.Timeout(float(self.timeout_ms) / 1000.0)
        verify = self._resolve_verify()
        for _ in range(self.retry_count + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout, verify=verify) as client:
                    response = await client.post(url, json=body_json, headers=headers)
                if response.status_code >= 500:
                    raise OmegaUnavailableError(f"omega upstream server error: {response.status_code}")
                if response.status_code >= 400:
                    raise OmegaRejectedError(
                        status_code=response.status_code,
                        detail_code=self._detail_code(response),
                        response_body=response.text,
                    )
                try:
                    data = response.json()
                except Exception as exc:
                    raise OmegaClientError("omega invalid json response") from exc
                self._record_success()
                return data
            except OmegaRejectedError:
                # Client-side payload/auth rejection from Omega should not open the circuit.
                raise
            except httpx.TimeoutException as exc:
                last_error = OmegaTimeoutError("omega timeout")
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.NetworkError, httpx.ProtocolError) as exc:
                last_error = OmegaUnavailableError(f"omega upstream connection error: {exc}")
            except OmegaUnavailableError as exc:
                last_error = exc
            except Exception as exc:
                last_error = exc
        # Count one failure per request after all retries are exhausted.
        self._record_failure()
        if isinstance(last_error, OmegaClientError):
            raise last_error
        raise OmegaClientError(str(last_error) if last_error else "omega upstream request failed")
