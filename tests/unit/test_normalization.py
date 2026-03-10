from __future__ import annotations

from connector.app import _fallback_response, _normalize_response
from connector.models import ScanAttachmentRequest


def test_normalize_response_clamps_values() -> None:
    req = ScanAttachmentRequest(tenant_id="tenant-a", request_id="req-1", extracted_text="x")
    out = _normalize_response(
        {
            "request_id": "req-1",
            "tenant_id": "tenant-a",
            "risk_score": 999,
            "verdict": "unexpected",
            "reasons": ["r1"],
            "evidence_id": "ev-1",
            "policy_trace": {},
        },
        req,
    )
    assert out.risk_score == 100
    assert out.verdict == "quarantine"


def test_fallback_response_uses_fail_mode() -> None:
    req = ScanAttachmentRequest(tenant_id="tenant-a", request_id="req-2", extracted_text="x")
    out = _fallback_response(
        payload=req,
        reason="omega_rejected_4xx",
        fail_mode="block",
        detail_code="invalid_file_base64",
        upstream_status=400,
    )
    assert out.verdict == "block"
    assert out.risk_score == 95
    assert "omega_rejected_4xx" in out.reasons
    assert out.policy_trace["upstream_detail_code"] == "invalid_file_base64"
    assert out.policy_trace["upstream_status"] == 400
