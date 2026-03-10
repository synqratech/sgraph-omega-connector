## Summary

Describe what changed and why.

## Change Type

- [ ] Fix
- [ ] Feature
- [ ] Docs
- [ ] Refactor
- [ ] Contract/API change

## Validation

- [ ] `make test`
- [ ] `RUN_COMPOSE_E2E=1 .venv/bin/pytest -s tests/e2e/test_compose_scenarios.py` (or explained why not run)
- [ ] Updated docs/openapi/tests for behavior changes

## Contract Impact

- [ ] No contract impact
- [ ] Additive contract change (v1-safe)
- [ ] Breaking change (requires new version path/spec)

If contract changed, list updated files:

- `contracts/openapi/connector-v1.yaml`
- `contracts/schemas/*`
- `docs/CONTRACT.md`

## Security/Privacy Check

- [ ] No secrets/tokens added
- [ ] No plaintext sensitive payload logging introduced
- [ ] Replay/auth/fail-mode behavior preserved
