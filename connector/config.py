from __future__ import annotations

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str, default: int) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    connector_host: str
    connector_port: int
    connector_api_keys: list[str]
    connector_require_hmac: bool
    connector_hmac_secret: str
    connector_fail_mode: str
    connector_debug_document_scan: bool

    log_level: str
    audit_redaction: bool
    nonce_ttl_sec: int
    max_clock_skew_sec: int

    omega_base_url: str
    omega_api_key: str
    omega_require_hmac: bool
    omega_hmac_secret: str
    omega_tls_verify: bool
    omega_ca_cert_path: str
    omega_timeout_ms: int
    omega_retry_count: int
    omega_circuit_breaker_fails: int
    omega_circuit_breaker_reset_sec: int


def load_settings() -> Settings:
    keys_raw = os.getenv("CONNECTOR_API_KEYS", "")
    api_keys = [item.strip() for item in keys_raw.split(",") if item.strip()]
    fail_mode = os.getenv("CONNECTOR_FAIL_MODE", "quarantine").strip().lower()
    if fail_mode not in {"allow", "quarantine", "block"}:
        fail_mode = "quarantine"

    return Settings(
        connector_host=os.getenv("CONNECTOR_HOST", "0.0.0.0"),
        connector_port=_as_int(os.getenv("CONNECTOR_PORT"), 18080),
        connector_api_keys=api_keys,
        connector_require_hmac=_as_bool(os.getenv("CONNECTOR_REQUIRE_HMAC"), True),
        connector_hmac_secret=os.getenv("CONNECTOR_HMAC_SECRET", ""),
        connector_fail_mode=fail_mode,
        connector_debug_document_scan=_as_bool(os.getenv("CONNECTOR_DEBUG_DOCUMENT_SCAN"), False),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        audit_redaction=_as_bool(os.getenv("AUDIT_REDACTION"), True),
        nonce_ttl_sec=_as_int(os.getenv("NONCE_TTL_SEC"), 600),
        max_clock_skew_sec=_as_int(os.getenv("MAX_CLOCK_SKEW_SEC"), 300),
        omega_base_url=os.getenv("OMEGA_BASE_URL", "http://omega-api:8080"),
        omega_api_key=os.getenv("OMEGA_API_KEY", ""),
        omega_require_hmac=_as_bool(os.getenv("OMEGA_REQUIRE_HMAC"), True),
        omega_hmac_secret=os.getenv("OMEGA_HMAC_SECRET", ""),
        omega_tls_verify=_as_bool(os.getenv("OMEGA_TLS_VERIFY"), True),
        omega_ca_cert_path=os.getenv("OMEGA_CA_CERT_PATH", "").strip(),
        omega_timeout_ms=_as_int(os.getenv("OMEGA_TIMEOUT_MS"), 15000),
        omega_retry_count=_as_int(os.getenv("OMEGA_RETRY_COUNT"), 2),
        omega_circuit_breaker_fails=_as_int(os.getenv("OMEGA_CIRCUIT_BREAKER_FAILS"), 5),
        omega_circuit_breaker_reset_sec=_as_int(os.getenv("OMEGA_CIRCUIT_BREAKER_RESET_SEC"), 30),
    )
