# Contracts v1

This folder is the canonical contract source for the connector.

## Compatibility policy

- v1 is additive-only.
- Do not rename or remove public fields.
- Unknown fields must be ignored by readers.
- Backward compatibility is validated by `tests/e2e/test_openapi_contract.py`.

## Files

- `openapi/connector-v1.yaml`: SGraph-facing OpenAPI contract.
- `schemas/snapshots/*.schema.json`: frozen validation snapshots.
- `schemas/examples/`: golden request/response payloads.

## Governance

- Human-readable contract and auth details: `docs/CONTRACT.md`.
- Contract change process and release checklist: `docs/CONTRACT_CHANGE_POLICY.md`.
