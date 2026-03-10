from __future__ import annotations

import argparse
import base64
import json
import ssl
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from scripts.signature_helper import build_headers


def _post_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_sec: int,
) -> tuple[int, dict[str, Any], int]:
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url=url, method="POST", data=body, headers=headers)
    ctx = ssl._create_unverified_context() if url.startswith("https://") else None
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout_sec) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), (json.loads(raw) if raw else {}), len(body)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except Exception:
            parsed = {"raw": raw}
        return int(exc.code), parsed, len(body)


def _mk_bytes(size: int) -> bytes:
    # Deterministic payload to make runs reproducible.
    seed = b"SGraphOmegaConnectorBoundary20MB"
    out = bytearray()
    while len(out) < size:
        out.extend(seed)
    return bytes(out[:size])


def run(args: argparse.Namespace) -> list[dict[str, Any]]:
    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}{args.path}"
    mb20 = 20 * 1024 * 1024
    file_sizes = [
        ("file_boundary_minus_1k", mb20 - 1024),
        ("file_boundary_exact_20mb", mb20),
        ("file_boundary_plus_1k", mb20 + 1024),
    ]

    out: list[dict[str, Any]] = []
    for name, sz in file_sizes:
        raw = _mk_bytes(sz)
        payload = {
            "tenant_id": args.tenant_id,
            "request_id": f"{name}-{uuid.uuid4().hex[:8]}",
            "filename": f"{name}.bin",
            "mime": "application/octet-stream",
            "file_base64": base64.b64encode(raw).decode("ascii"),
            "metadata": {"suite": "boundary_20mb_via_connector"},
        }
        headers = build_headers(
            secret=args.hmac_secret,
            api_key=args.api_key,
            path=args.path,
            payload=payload,
        )
        status, response, body_len = _post_json(
            url=endpoint,
            payload=payload,
            headers=headers,
            timeout_sec=args.timeout_sec,
        )
        out.append(
            {
                "scenario": name,
                "file_size_bytes": sz,
                "request_body_bytes": body_len,
                "http_status": status,
                "response": response,
            }
        )
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Boundary test around 20MB via Connector API.")
    parser.add_argument("--base-url", default="https://localhost:8088")
    parser.add_argument("--path", default="/v1/scan/attachment")
    parser.add_argument("--api-key", default="local-connector-key")
    parser.add_argument("--hmac-secret", default="local-connector-hmac")
    parser.add_argument("--tenant-id", default="tenant-boundary-20mb")
    parser.add_argument("--timeout-sec", type=int, default=120)
    parser.add_argument(
        "--out",
        default="artifacts/qualification/boundary_20mb_via_connector_after_proxy_limit.json",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
