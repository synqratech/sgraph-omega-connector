from __future__ import annotations

import argparse
import base64
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from scripts.e2e_sgraph_real_path import (
    _build_scenarios,
    _decrypt_like_sgraph_ui,
    _encrypt_like_sgraph_ui,
    _extract_sgmeta_or_raw,
    _http_bytes,
    _http_json,
    _package_with_sgmeta,
    _sha256_hex,
)


def run(args: argparse.Namespace) -> dict[str, Any]:
    base = args.base_url.rstrip("/")
    sgraph_base = f"{base}/sgraph"
    sgraph_scan_url = f"{sgraph_base}{args.sgraph_scan_path}"
    sgraph_headers_json = {
        "Content-Type": "application/json",
        "x-sgraph-access-token": args.sgraph_access_token,
    }
    sgraph_headers_bytes = {
        "Content-Type": "application/octet-stream",
        "x-sgraph-access-token": args.sgraph_access_token,
    }

    results: list[dict[str, Any]] = []
    for scenario in _build_scenarios():
        packaged_plain = _package_with_sgmeta(scenario.content, scenario.filename)
        key, encrypted_payload = _encrypt_like_sgraph_ui(packaged_plain)

        create_status, create_body = _http_json(
            method="POST",
            url=f"{sgraph_base}/api/transfers/create",
            body={"file_size_bytes": len(packaged_plain), "content_type_hint": scenario.mime},
            headers=sgraph_headers_json,
        )
        if create_status != 200:
            raise RuntimeError(f"sgraph create failed for {scenario.name}: {create_status} {create_body}")
        transfer_id = str(create_body.get("transfer_id") or "")
        if not transfer_id:
            raise RuntimeError(f"sgraph create missing transfer_id for {scenario.name}: {create_body}")

        upload_status, upload_raw = _http_bytes(
            method="POST",
            url=f"{sgraph_base}/api/transfers/upload/{transfer_id}",
            body=encrypted_payload,
            headers=sgraph_headers_bytes,
        )
        if upload_status != 200:
            raise RuntimeError(
                f"sgraph upload failed for {scenario.name}: {upload_status} {upload_raw.decode('utf-8', errors='replace')}"
            )

        complete_status, complete_body = _http_json(
            method="POST",
            url=f"{sgraph_base}/api/transfers/complete/{transfer_id}",
            body={},
            headers=sgraph_headers_json,
        )
        if complete_status != 200:
            raise RuntimeError(f"sgraph complete failed for {scenario.name}: {complete_status} {complete_body}")

        download_status, downloaded_encrypted = _http_bytes(
            method="GET",
            url=f"{sgraph_base}/api/transfers/download/{transfer_id}",
            headers={"x-sgraph-access-token": args.sgraph_access_token},
        )
        if download_status != 200:
            raise RuntimeError(
                f"sgraph download failed for {scenario.name}: {download_status} {downloaded_encrypted.decode('utf-8', errors='replace')}"
            )

        decrypted = _decrypt_like_sgraph_ui(key, downloaded_encrypted)
        meta, decrypted_content = _extract_sgmeta_or_raw(decrypted)

        request_id = f"sgraph-upstream-{scenario.name}-{uuid.uuid4().hex[:10]}"
        scan_payload = {
            "tenant_id": args.tenant_id,
            "request_id": request_id,
            "filename": str((meta or {}).get("filename") or scenario.filename),
            "mime": scenario.mime,
            "file_base64": base64.b64encode(decrypted_content).decode("ascii"),
            "metadata": {
                "flow": "sgraph-route-to-connector",
                "sgraph_transfer_id": transfer_id,
                "scenario": scenario.name,
            },
        }

        scan_status, scan_body = _http_json(
            method="POST",
            url=sgraph_scan_url,
            body=scan_payload,
            headers=sgraph_headers_json,
            timeout=args.scan_timeout_sec,
        )
        if scan_status != 200:
            raise RuntimeError(f"sgraph connector scan failed for {scenario.name}: {scan_status} {scan_body}")

        reasons = [str(x) for x in scan_body.get("reasons", [])]
        fallback_reasons = [r for r in reasons if r.startswith("omega_") or r in {"omega_timeout", "omega_unavailable"}]
        if args.strict_no_fallback and fallback_reasons:
            raise RuntimeError(f"fallback detected for {scenario.name}: {fallback_reasons}")

        results.append(
            {
                "scenario": scenario.name,
                "sgraph": {
                    "transfer_id": transfer_id,
                    "uploaded_encrypted_sha256": _sha256_hex(encrypted_payload),
                    "downloaded_encrypted_sha256": _sha256_hex(downloaded_encrypted),
                    "encrypted_roundtrip_match": encrypted_payload == downloaded_encrypted,
                },
                "decrypt": {
                    "sgmeta_metadata": meta,
                    "decrypted_content_sha256": _sha256_hex(decrypted_content),
                    "decrypted_content_size": len(decrypted_content),
                },
                "sgraph_connector_response": scan_body,
            }
        )

    return {
        "base_url": base,
        "tenant_id": args.tenant_id,
        "sgraph_scan_path": args.sgraph_scan_path,
        "sgraph_prefix": "/sgraph",
        "scenarios": results,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run real SGraph decrypt -> SGraph connector route -> connector -> omega e2e."
    )
    parser.add_argument("--base-url", default="https://localhost:8088")
    parser.add_argument("--sgraph-access-token", default="dev-local-token")
    parser.add_argument("--tenant-id", default="tenant-sgraph-upstream-connector-e2e")
    parser.add_argument("--sgraph-scan-path", default="/api/integrations/connector/scan-attachment")
    parser.add_argument("--scan-timeout-sec", type=int, default=60)
    parser.add_argument("--strict-no-fallback", action="store_true", default=True)
    parser.add_argument("--allow-fallback", action="store_true", default=False)
    parser.add_argument(
        "--out",
        default="artifacts/qualification/sgraph_upstream_connector_path_decisions.json",
        help="Path to save full result JSON.",
    )
    args = parser.parse_args(argv)
    if args.allow_fallback:
        args.strict_no_fallback = False
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    result = run(args)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
