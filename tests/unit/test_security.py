from __future__ import annotations

from connector.auth import AuthConfig, AuthValidator
from connector.security import NonceReplayCache, build_canonical_string, sign_canonical


def test_canonical_and_signature_are_stable() -> None:
    canonical = build_canonical_string(
        method="POST",
        path="/v1/scan/attachment",
        body_sha256_hex="abc123",
        tenant_id="tenant-a",
        request_id="req-1",
        timestamp="1700000000",
        nonce="nonce-1",
    )
    signature = sign_canonical(canonical, "secret")
    assert canonical == "POST\n/v1/scan/attachment\nabc123\ntenant-a\nreq-1\n1700000000\nnonce-1"
    assert isinstance(signature, str)
    assert len(signature) >= 10


def test_api_key_validation_plain_and_sha256() -> None:
    validator = AuthValidator(
        AuthConfig(
            api_keys=["plain-key", "sha256:a4ae87b73fa5645e6aee415a6f72be4dcbd99d057a7b40cb1b867c181d179260"],
            require_hmac=False,
            hmac_secret="",
            max_clock_skew_sec=300,
        ),
        replay_cache=NonceReplayCache(ttl_sec=60, max_entries=1000),
    )
    assert validator.validate_api_key("plain-key") == "plain-key"
    assert validator.validate_api_key("hashed-key") == "hashed-key"


def test_replay_cache_duplicate_nonce_rejected() -> None:
    cache = NonceReplayCache(ttl_sec=60, max_entries=100)
    assert cache.check_and_mark("k1") is True
    assert cache.check_and_mark("k1") is False
