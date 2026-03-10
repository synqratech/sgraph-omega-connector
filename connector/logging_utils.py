from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

LOGGER = logging.getLogger("connector.audit")


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def audit_log(
    *,
    request_id: str,
    tenant_id: str,
    verdict: str,
    risk_score: int,
    reasons: list[str],
    redact: bool,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "event": "connector_scan_audit",
        "request_id": request_id,
        "tenant_id": _hash(tenant_id) if redact else tenant_id,
        "verdict": verdict,
        "risk_score": int(risk_score),
        "reasons": list(reasons),
    }
    if extra:
        payload["extra"] = extra
    LOGGER.info("%s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
