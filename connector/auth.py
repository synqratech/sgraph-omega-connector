from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

from fastapi import Request

from connector.errors import http_error
from connector.models import ScanAttachmentRequest
from connector.security import NonceReplayCache, build_canonical_string, sha256_hex, sign_canonical


@dataclass(frozen=True)
class AuthConfig:
    api_keys: list[str]
    require_hmac: bool
    hmac_secret: str
    max_clock_skew_sec: int


class AuthValidator:
    def __init__(self, config: AuthConfig, replay_cache: NonceReplayCache) -> None:
        self.config = config
        self.replay_cache = replay_cache

    def validate_api_key(self, provided: str | None, *, request_id: str | None = None) -> str:
        key = str(provided or "").strip()
        if not key:
            raise http_error(401, "unauthorized", "missing API key", request_id=request_id)
        for configured in self.config.api_keys:
            item = configured.strip()
            if not item:
                continue
            if item.startswith("sha256:"):
                digest = item.split(":", 1)[1].strip().lower()
                if hashlib.sha256(key.encode("utf-8")).hexdigest() == digest:
                    return key
                continue
            if hmac.compare_digest(item, key):
                return key
        raise http_error(401, "unauthorized", "invalid API key", request_id=request_id)

    def validate_hmac(
        self,
        *,
        request: Request,
        body_bytes: bytes,
        payload: ScanAttachmentRequest,
        provided_api_key: str,
    ) -> None:
        if not self.config.require_hmac:
            return
        sig = str(request.headers.get("X-Signature", "")).strip()
        ts_raw = str(request.headers.get("X-Timestamp", "")).strip()
        nonce = str(request.headers.get("X-Nonce", "")).strip()
        if not sig or not ts_raw or not nonce:
            raise http_error(401, "invalid_signature", "missing signature headers", request_id=payload.request_id)

        try:
            ts_i = int(ts_raw)
        except Exception:
            raise http_error(401, "invalid_signature", "invalid timestamp", request_id=payload.request_id)

        now_i = int(time.time())
        if abs(now_i - ts_i) > int(self.config.max_clock_skew_sec):
            raise http_error(401, "stale_timestamp", "timestamp outside accepted skew", request_id=payload.request_id)

        if not self.config.hmac_secret:
            raise http_error(401, "invalid_signature", "server hmac secret not configured", request_id=payload.request_id)

        canonical = build_canonical_string(
            method=request.method,
            path=request.url.path,
            body_sha256_hex=sha256_hex(body_bytes),
            tenant_id=payload.tenant_id,
            request_id=str(payload.request_id or ""),
            timestamp=ts_raw,
            nonce=nonce,
        )
        expected = sign_canonical(canonical, self.config.hmac_secret)
        if not hmac.compare_digest(expected, sig):
            raise http_error(401, "invalid_signature", "signature verification failed", request_id=payload.request_id)

        replay_key = sha256_hex(f"{payload.tenant_id}|{hashlib.sha256(provided_api_key.encode('utf-8')).hexdigest()}|{nonce}".encode("utf-8"))
        if not self.replay_cache.check_and_mark(replay_key):
            raise http_error(409, "replay_detected", "nonce already used", request_id=payload.request_id)
