from __future__ import annotations

import base64
import os
from typing import Any

from sgraph_ai_app_send.integrations.connector_client import (
    ConnectorClientConfig,
    SGraphOmegaConnectorClient,
)


def scan_decrypted_file_for_agent(
    *,
    tenant_id: str,
    request_id: str,
    filename: str,
    mime: str,
    decrypted_bytes: bytes,
) -> dict[str, Any]:
    client = SGraphOmegaConnectorClient(
        ConnectorClientConfig(
            base_url=os.environ["SGRAPH_CONNECTOR_BASE_URL"],
            api_key=os.environ["SGRAPH_CONNECTOR_API_KEY"],
            hmac_secret=os.environ["SGRAPH_CONNECTOR_HMAC_SECRET"],
            timeout_sec=int(os.getenv("SGRAPH_CONNECTOR_TIMEOUT_SEC", "30")),
        )
    )
    payload = {
        "tenant_id": tenant_id,
        "request_id": request_id,
        "filename": filename,
        "mime": mime,
        "file_base64": base64.b64encode(decrypted_bytes).decode("ascii"),
        "metadata": {"source": "sgraph_trusted_flow"},
    }
    return client.scan_attachment(payload)


def enforce_verdict(scan_result: dict[str, Any]) -> str:
    verdict = str(scan_result.get("verdict", "quarantine")).strip().lower()
    if verdict == "allow":
        return "allow"
    if verdict == "block":
        raise RuntimeError("blocked by omega connector policy")
    return "quarantine"
