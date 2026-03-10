from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from typing import Any


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(
    *,
    method: str,
    path: str,
    body_bytes: bytes,
    tenant_id: str,
    request_id: str,
    timestamp: str,
    nonce: str,
) -> str:
    return "\n".join(
        [
            method.upper().strip(),
            path.strip(),
            _sha256_hex(body_bytes),
            tenant_id.strip(),
            request_id.strip(),
            timestamp.strip(),
            nonce.strip(),
        ]
    )


@dataclass(frozen=True)
class ConnectorClientConfig:
    base_url: str
    api_key: str
    hmac_secret: str
    timeout_sec: int = 30
    path_scan_attachment: str = "/v1/scan/attachment"


class ConnectorClientError(RuntimeError):
    pass


class SGraphOmegaConnectorClient:
    def __init__(self, config: ConnectorClientConfig) -> None:
        self.config = config

    def _sign_headers(self, *, payload: dict[str, Any], body_bytes: bytes) -> dict[str, str]:
        request_id = str(payload.get("request_id") or "")
        tenant_id = str(payload.get("tenant_id") or "")
        ts = str(int(time.time()))
        nonce = str(uuid.uuid4())
        canonical = _canonical(
            method="POST",
            path=self.config.path_scan_attachment,
            body_bytes=body_bytes,
            tenant_id=tenant_id,
            request_id=request_id,
            timestamp=ts,
            nonce=nonce,
        )
        signature = _b64url(
            hmac.new(
                self.config.hmac_secret.encode("utf-8"),
                canonical.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        )
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.config.api_key,
            "X-Timestamp": ts,
            "X-Nonce": nonce,
            "X-Signature": signature,
        }

    def scan_attachment(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        headers = self._sign_headers(payload=payload, body_bytes=body)
        url = f"{self.config.base_url.rstrip('/')}{self.config.path_scan_attachment}"
        req = urllib.request.Request(url=url, method="POST", data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not isinstance(data, dict):
                    raise ConnectorClientError("connector response is not an object")
                return data
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise ConnectorClientError(f"connector http error {exc.code}: {raw}") from exc
        except Exception as exc:
            raise ConnectorClientError(f"connector request failed: {exc}") from exc
