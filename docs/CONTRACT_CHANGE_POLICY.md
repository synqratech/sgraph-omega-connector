# Contract Change Policy (v1)

## 1. Versioning Rules

- `v1` is additive-only.
- Forbidden in `v1`:
  - removing fields,
  - renaming fields,
  - changing field types incompatibly,
  - changing meaning of existing fields.
- Breaking changes require a new major contract version (`v2` path/spec).

## 2. Mandatory Files to Update

Any contract change must update all relevant artifacts together:

- `contracts/openapi/connector-v1.yaml`
- `contracts/schemas/snapshots/*.schema.json`
- `contracts/schemas/examples/**/*`
- `docs/CONTRACT.md` (if behavior/auth/error semantics changed)
- tests that enforce contract behavior

## 3. Required Validation Before Merge

- `make test-contracts`
- `pytest -q tests/unit tests/integration`
- `RUN_COMPOSE_E2E=1 pytest -q tests/e2e/test_compose_scenarios.py` (when runtime behavior changed)

## 4. Change Types

Additive-safe examples:

- new optional field in request/response,
- new `metadata` subkeys,
- new `policy_trace` subfields.

Breaking examples:

- changing `risk_score` from integer to string,
- removing `evidence_id`,
- changing verdict enum values.

## 5. PR Checklist

- OpenAPI updated.
- Snapshots/examples updated.
- Contract tests green.
- Runtime behavior and docs aligned.
- Release notes include explicit contract delta.

## 6. Upstream Coordination

When SGraph/Omega integration behavior changes:

- update `upstream_patches/` files and instructions,
- include exact target paths and hook points,
- document required env changes.
