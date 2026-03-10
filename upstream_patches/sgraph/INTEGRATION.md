# SGraph Integration Instructions

## 1. Purpose

Add an explicit SGraph-side adapter that sends decrypted content to connector.

This is performed only inside trusted flow after decrypt.

## 2. Target placement in SGraph repo

Recommended target paths in your SGraph repository:

- `sgraph_ai_app_send/integrations/connector_client.py` (copy from this patch kit)
- `sgraph_ai_app_send/integrations/connector_hook.py` (compose payload + call client)

## 3. Runtime hook point

Hook must run after decrypt, before ingestion into downstream agent/workspace.

Suggested sequence:

1. Decrypt payload.
2. Build connector request:
   - `tenant_id`
   - `request_id`
   - `filename`, `mime`
   - `file_base64` or `extracted_text`
3. Call connector.
4. Enforce verdict:
   - `allow` -> continue
   - `quarantine` -> require review
   - `block` -> hard stop

See `connector_hook.py`.

## 4. Required env in SGraph runtime

- `SGRAPH_CONNECTOR_BASE_URL` (for example `https://connector.example.internal`)
- `SGRAPH_CONNECTOR_API_KEY`
- `SGRAPH_CONNECTOR_HMAC_SECRET`
- `SGRAPH_CONNECTOR_TIMEOUT_SEC` (optional)

## 5. Contract pin

SGraph caller must pin to:

- `POST /v1/scan/attachment`
- Request/response model from `contracts/openapi/connector-v1.yaml`

## 6. Operational notes

- Do not log plaintext payloads.
- Preserve `request_id` across SGraph -> Connector -> Omega trace.
- Retry policy should be conservative; connector already includes upstream retry/fallback.
