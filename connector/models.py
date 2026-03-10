from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScanAttachmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    request_id: Optional[str] = None
    filename: Optional[str] = None
    mime: Optional[str] = None
    file_base64: Optional[str] = None
    extracted_text: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_input_payload(self) -> "ScanAttachmentRequest":
        if not (self.file_base64 or self.extracted_text):
            raise ValueError("one of file_base64 or extracted_text is required")
        return self


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    request_id: Optional[str] = None
    error: ErrorEnvelope


class ScanAttachmentResponse(BaseModel):
    request_id: str
    tenant_id: str
    risk_score: int = Field(ge=0, le=100)
    verdict: str
    reasons: list[str] = Field(default_factory=list)
    evidence_id: str
    policy_trace: dict[str, Any] = Field(default_factory=dict)
    attestation: Optional[dict[str, Any]] = None
