from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import time
import uuid
from typing import Any


def b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def build_canonical(method: str, path: str, body_bytes: bytes, tenant_id: str, request_id: str, ts: str, nonce: str) -> str:
    body_hash = hashlib.sha256(body_bytes).hexdigest()
    return "\n".join([method.upper(), path, body_hash, tenant_id, request_id, ts, nonce])


def sign(secret: str, canonical: str) -> str:
    return b64url(hmac.new(secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).digest())


def build_headers(*, secret: str, api_key: str, path: str, payload: dict[str, Any]) -> dict[str, str]:
    request_id = str(payload.get("request_id") or "")
    tenant_id = str(payload.get("tenant_id") or "")
    body_bytes = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ts = str(int(time.time()))
    nonce = str(uuid.uuid4())
    canonical = build_canonical("POST", path, body_bytes, tenant_id, request_id, ts, nonce)
    return {
        "X-API-Key": api_key,
        "X-Timestamp": ts,
        "X-Nonce": nonce,
        "X-Signature": sign(secret, canonical),
        "Content-Type": "application/json",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build connector HMAC headers")
    parser.add_argument("--secret", required=True)
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--path", default="/v1/scan/attachment")
    parser.add_argument("--payload", required=True, help="JSON payload")
    args = parser.parse_args()

    payload = json.loads(args.payload)
    headers = build_headers(secret=args.secret, api_key=args.api_key, path=args.path, payload=payload)
    print(json.dumps(headers, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
