from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def build_canonical_string(
    *,
    method: str,
    path: str,
    body_sha256_hex: str,
    tenant_id: str,
    request_id: str,
    timestamp: str,
    nonce: str,
) -> str:
    return "\n".join(
        [
            str(method).upper().strip(),
            str(path).strip(),
            str(body_sha256_hex).strip(),
            str(tenant_id).strip(),
            str(request_id).strip(),
            str(timestamp).strip(),
            str(nonce).strip(),
        ]
    )


def sign_canonical(canonical: str, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest()
    return b64url_encode(digest)


@dataclass
class NonceReplayCache:
    ttl_sec: int
    max_entries: int

    def __post_init__(self) -> None:
        self._entries: dict[str, float] = {}

    def _cleanup(self, now_ts: float) -> None:
        expired = [k for k, exp in self._entries.items() if exp <= now_ts]
        for key in expired:
            self._entries.pop(key, None)
        if len(self._entries) <= self.max_entries:
            return
        sorted_items = sorted(self._entries.items(), key=lambda x: x[1])
        overflow = len(self._entries) - self.max_entries
        for key, _ in sorted_items[:overflow]:
            self._entries.pop(key, None)

    def check_and_mark(self, key: str) -> bool:
        now_ts = time.time()
        self._cleanup(now_ts)
        if key in self._entries:
            return False
        self._entries[key] = now_ts + float(self.ttl_sec)
        return True
