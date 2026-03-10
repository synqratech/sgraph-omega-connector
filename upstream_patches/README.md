# Upstream Patch Kit

This directory contains integration patch assets for two upstream repositories:

- `SGraph` application repository
- `Omega` application repository

## Contents

- `COPY_PASTE_CHECKLIST.md`
  - file mapping (`source -> target`) for PRs in both upstream repos.
- `sgraph/connector_client.py`
  - drop-in Python client for calling connector with `X-API-Key + HMAC`.
- `sgraph/connector_hook.py`
  - hook functions for calling connector and enforcing verdict.
- `sgraph/env.connector.example`
  - required SGraph env template for connector calls.
- `sgraph/INTEGRATION.md`
  - exact placement and hook points in SGraph trusted flow.
- `omega/INTEGRATION.md`
  - required Omega-side config alignment and deployment notes.
- `omega/api.yml.connector-overlay.yaml`
  - Omega API config overlay template for connector alignment.
- `omega/env.required.txt`
  - required Omega runtime env keys for connector auth alignment.

## How to use

1. Copy files from `upstream_patches/sgraph/` into your SGraph repository target paths.
2. Apply hook from `sgraph/INTEGRATION.md` in trusted decrypt workflow.
3. Align Omega config using `upstream_patches/omega/INTEGRATION.md` in your Omega repository.
4. Run connector contract tests and live smoke.
