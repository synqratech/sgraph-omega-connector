# Contributing

Thanks for contributing to `sgraph-omega-connector`.

## Scope

This repository owns integration glue between SGraph and Omega:

- connector runtime,
- contract artifacts,
- integration tests,
- deployment and runbooks.

## Before opening a PR

1. Open an issue for non-trivial changes (feature, behavior change, contract updates).
2. Keep changes focused; avoid unrelated refactors in the same PR.
3. If you change contract/runtime behavior, update docs and tests in the same PR.

## Local setup

```bash
make bootstrap
```

Start local stack:

```bash
make up
make health
```

## Required checks

Run before PR:

```bash
make test
RUN_COMPOSE_E2E=1 .venv/bin/pytest -s tests/e2e/test_compose_scenarios.py
```

If your environment cannot run compose e2e, mention it explicitly in PR notes.

## Contract changes policy

For API/contract changes, follow:

- `docs/CONTRACT_CHANGE_POLICY.md`

Required updates for contract changes:

- `contracts/openapi/connector-v1.yaml`
- schema snapshots/examples
- relevant docs in `docs/`
- tests enforcing new behavior

## Pull request checklist

1. Problem statement is clear.
2. Tests cover changed behavior.
3. Documentation is updated.
4. No secrets or private paths added.
5. Changelog entry added when behavior changes.

## Coding standards

- Python 3.11+ compatible.
- Prefer small, explicit functions.
- Keep security paths readable and test-covered.
- Do not log plaintext sensitive content.

## How to report bugs

Use GitHub Issues and include:

- expected vs actual behavior,
- reproduction steps,
- environment details (OS, Python, docker compose),
- logs with sensitive values redacted.

## Security issues

Do not report vulnerabilities in public issues.

Use instructions in:

- `SECURITY.md`
