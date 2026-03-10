from __future__ import annotations

import argparse
import os


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Connector -> Omega upstream transport configuration")
    parser.add_argument("--omega-base-url", default=None)
    parser.add_argument("--require-https", action="store_true", default=True)
    parser.add_argument("--require-prefix", default="/omega")
    args = parser.parse_args()

    omega_base_url = (args.omega_base_url or os.getenv("OMEGA_BASE_URL", "")).strip()
    if not omega_base_url:
        print("fail: OMEGA_BASE_URL is empty")
        return 1

    if args.require_https and not omega_base_url.startswith("https://"):
        print(f"fail: OMEGA_BASE_URL must start with https://, got: {omega_base_url}")
        return 1

    if args.require_prefix and args.require_prefix not in omega_base_url:
        print(f"fail: OMEGA_BASE_URL must include '{args.require_prefix}', got: {omega_base_url}")
        return 1

    print(f"ok: OMEGA_BASE_URL={omega_base_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
