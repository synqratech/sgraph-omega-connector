# Omega Integration Instructions

## 1. Purpose

Define Omega-side requirements for connector integration.

No SGraph-specific runtime adapter is required in Omega runtime. Connector talks to Omega using Omega's existing API contract.

## 2. Omega endpoints used by connector

- `POST /v1/scan/attachment`
- Optional debug passthrough: `POST /v1/scan/attachment/document_scan_report`

## 3. Required Omega config alignment

Reference file in Omega repo:

- `config/api.yml`

Required settings:

- `api.security.transport_mode: proxy_tls`
- `api.security.require_https: true`
- `api.auth.api_keys` includes connector upstream key (`OMEGA_API_KEY` in connector env)
- `api.auth.require_hmac: true`
- `api.auth.hmac_secret_env` must match deployed env var containing shared secret
- `api.limits.max_file_bytes` aligned with connector/proxy body limits

## 4. Connector->Omega secret mapping

Connector env:

- `OMEGA_API_KEY`
- `OMEGA_HMAC_SECRET`

Omega env:

- value referenced by `api.auth.hmac_secret_env` (default `OMEGA_API_HMAC_SECRET`)

Secrets must match.

## 5. Deployment note

If Omega enforces HTTPS/proxy headers, connector must call Omega through TLS-aware proxy endpoint:

- example: `OMEGA_BASE_URL=https://reverse-proxy:8088/omega`

## 6. Optional attestation

If Omega attestation is enabled (`api.attestation.enabled: true`), connector forwards `attestation` field as pass-through.
