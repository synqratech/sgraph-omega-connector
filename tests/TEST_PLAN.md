# Test Plan Matrix

## Unit

- HMAC canonical string and signature generation stability.
- API key validation (plain + hashed key support).
- Replay nonce duplicate rejection.
- Response normalization and fail-mode fallback mapping.

## Integration

- Connector -> Omega happy path.
- Connector fallback on upstream timeout / upstream error.
- Debug endpoint guard behavior via `CONNECTOR_DEBUG_DOCUMENT_SCAN`.
- Unauthorized request rejection (`X-API-Key` invalid).

## E2E (Compose)

- Allow scenario: benign extracted text.
- Quarantine scenario: upstream 4xx fallback (`omega_rejected_4xx`) with detail-code propagation.
- Block scenario: exfiltration-heavy text.
- Security negative scenarios: invalid API key, stale timestamp, invalid signature, replay nonce.
- Payload negatives: missing payload, invalid base64, oversize extracted text.
- Resilience: `omega_rejected_4xx` classification and verification that 4xx rejections do not trip connector circuit-breaker.
- SGraph path smoke via reverse-proxy (`/sgraph/api/docs`).

## Performance

- k6 baseline profile (100 RPS target, 15m, weighted allow/quarantine/block).
- k6 stress profile (ramp 100->200->300 RPS).
- Report generation from k6 summaries (`artifacts/perf/perf-report.{json,md}`).

## Qualification Report

- Runtime qualification sampler writes:
  - verdict matrix
  - error-rate
  - fallback-rate
  - p50/p95/p99 latency
  - GO/NO-GO decision with blockers

## Contract

- OpenAPI path existence checks.
- JSON examples validated against frozen schema snapshots.
- Backward compatibility policy for v1: additive-only, no field rename/removal.
