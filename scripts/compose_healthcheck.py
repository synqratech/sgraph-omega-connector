from __future__ import annotations

import argparse
import json
import ssl
import urllib.request


def fetch_json(url: str) -> dict:
    context = ssl._create_unverified_context() if url.startswith("https://") else None
    with urllib.request.urlopen(url, context=context, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_status(url: str) -> int:
    context = ssl._create_unverified_context() if url.startswith("https://") else None
    with urllib.request.urlopen(url, context=context, timeout=10) as resp:
        return int(resp.status)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local compose services")
    parser.add_argument("--base-url", default="https://localhost:8088")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    checks = {
        "connector": f"{base}/healthz",
        "omega": f"{base}/omega/healthz",
        "sgraph_docs": f"{base}/sgraph/api/docs",
    }

    failures = []
    for name, url in checks.items():
        try:
            if name == "sgraph_docs":
                status = fetch_status(url)
                data = {"status": "ok", "http_status": status}
            else:
                data = fetch_json(url)
            print(f"{name}: ok {data}")
        except Exception as exc:
            print(f"{name}: fail ({exc})")
            failures.append(name)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
