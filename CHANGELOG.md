# Changelog

All notable changes to `sgraph-omega-connector` are documented in this file.

This project follows a Keep a Changelog style and Semantic Versioning intent.

## [Unreleased] - 2026-03-09

### Added
- Initial integration-hub repository structure for SGraph <-> Omega connection.
- Connector service (`FastAPI`) with endpoints:
  - `GET /healthz`
  - `POST /v1/scan/attachment`
  - `POST /v1/scan/attachment/document_scan_report` (debug-gated)
- OpenAPI contract `v1` and schema/examples:
  - `contracts/openapi/connector-v1.yaml`
  - `contracts/schemas/*`
- Inbound security model:
  - `X-API-Key` validation
  - HMAC canonical signature validation
  - replay protection via nonce/timestamp cache
- Full local compose topology:
  - `connector`
  - `omega-api`
  - `sgraph-user-api`
  - `reverse-proxy` (TLS-terminated)
- Upstream patch kit and copy/paste checklist for two upstream repos:
  - `upstream_patches/sgraph/*`
  - `upstream_patches/omega/*`
  - `upstream_patches/COPY_PASTE_CHECKLIST.md`
- Qualification/testing scaffold:
  - unit/integration/contract/e2e structure
  - smoke/preflight/health/perf helper scripts
- Operations runbook:
  - `docs/OPS_RECOVERY.md`
- Central integration blueprint with end-to-end diagrams and side-by-side responsibilities:
  - `docs/INTEGRATION_ARCHITECTURE.md`
- Open-source community health files:
  - `LICENSE` (MIT)
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
- GitHub collaboration/quality automation:
  - issue templates (`.github/ISSUE_TEMPLATE/*`)
  - pull request template (`.github/PULL_REQUEST_TEMPLATE.md`)
  - CI workflow (`.github/workflows/ci.yml`)

### Changed
- Connector -> Omega default timeout raised to reduce false timeout fallback:
  - `OMEGA_TIMEOUT_MS` default set to `15000`.
- Local omega runtime deployment improved for stability:
  - prebuilt omega dependency image: `deploy/omega/Dockerfile`
  - compose omega startup switched to `uvicorn ... --workers`
  - `OMEGA_UVICORN_WORKERS` introduced in env templates
  - `OMEGA_OMP_NUM_THREADS` and `OMEGA_OPENBLAS_NUM_THREADS` introduced (default `1`)
  - omega service healthcheck/restart tuning in compose
- Added make targets for omega ops:
  - `omega-restart`
  - `omega-logs`
  - plus existing proxy/body-limit diagnostic targets
- E2E expectation updated:
  - omega `4xx` rejection path is validated as `omega_rejected_4xx` and should not trip circuit by itself.
- Repository documentation refreshed for OSS readability:
  - root `README.md` restructured (architecture, quickstart, test/qualification, doc map, upstream kit pointers)
  - `docs/README.md` extended with `INTEGRATION_ARCHITECTURE.md` index entry
- OSS sanitization pass:
  - `upstream_patches/*` rewritten to remove absolute local paths and private repo naming
  - local compose bind mounts switched to env-driven path variables (`OMEGA_REPO_PATH`, `SGRAPH_REPO_PATH`)
  - deploy docs and local env template updated for path configuration

### Fixed
- `413` ingress issue on `file_base64` payloads near ~1MB:
  - explicit `client_max_body_size 64m` policy in proxy config
  - config mounted into proxy container for deterministic local behavior
  - boundary probes around 1MB/5MB/20MB added and validated
- Connector circuit-breaker behavior corrected:
  - failures now counted once per request after retry exhaustion (not per retry attempt)
  - omega `4xx` rejections no longer open circuit
- Compose healthcheck script corrected to actually verify `sgraph_docs` HTTP status.

### Notes
- Integration remains isolated in this repository; upstream repos keep independent development.
- Live runtime behavior still depends on Omega service health and host resource envelope.
