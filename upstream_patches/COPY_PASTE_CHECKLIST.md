# Copy/Paste Checklist for Upstream PRs

Ниже универсальный чеклист для двух отдельных PR:

- PR-1 в SGraph repository
- PR-2 в Omega repository

Используем плейсхолдеры путей:

- `<connector-repo>`: путь к этому репозиторию (`sgraph-omega-connector`)
- `<sgraph-repo>`: путь к вашему SGraph репозиторию
- `<omega-repo>`: путь к вашему Omega репозиторию

## PR-1: SGraph Repository

### A. Файлы для копирования

1. Source:
   - `<connector-repo>/upstream_patches/sgraph/connector_client.py`
   Target:
   - `<sgraph-repo>/sgraph_ai_app_send/integrations/connector_client.py`

2. Source:
   - `<connector-repo>/upstream_patches/sgraph/connector_hook.py`
   Target:
   - `<sgraph-repo>/sgraph_ai_app_send/integrations/connector_hook.py`

3. Source:
   - `<connector-repo>/upstream_patches/sgraph/env.connector.example`
   Target:
   - `<sgraph-repo>/.env.connector.example`

### B. Команды copy/paste

```bash
export CONNECTOR_REPO=/path/to/sgraph-omega-connector
export SGRAPH_REPO=/path/to/sgraph-repo

mkdir -p "$SGRAPH_REPO/sgraph_ai_app_send/integrations"
cp "$CONNECTOR_REPO/upstream_patches/sgraph/connector_client.py" \
   "$SGRAPH_REPO/sgraph_ai_app_send/integrations/connector_client.py"
cp "$CONNECTOR_REPO/upstream_patches/sgraph/connector_hook.py" \
   "$SGRAPH_REPO/sgraph_ai_app_send/integrations/connector_hook.py"
cp "$CONNECTOR_REPO/upstream_patches/sgraph/env.connector.example" \
   "$SGRAPH_REPO/.env.connector.example"
```

### C. Что подключить в коде SGraph

1. В trusted decrypt flow (после расшифровки, до ingestion в agent) добавить вызов:
   - `run_connector_scan(...)`
   - `enforce_connector_verdict(...)`
2. Передавать стабильный `request_id` и `tenant_id`.
3. Не логировать plaintext.

Reference:

- `upstream_patches/sgraph/INTEGRATION.md`

## PR-2: Omega Repository

### A. Файлы для копирования

1. Source:
   - `<connector-repo>/upstream_patches/omega/api.yml.connector-overlay.yaml`
   Target (как reference/overlay рядом с конфигом):
   - `<omega-repo>/config/api.yml.connector-overlay.yaml`

2. Source:
   - `<connector-repo>/upstream_patches/omega/env.required.txt`
   Target:
   - `<omega-repo>/config/env.required.txt`

### B. Команды copy/paste

```bash
export CONNECTOR_REPO=/path/to/sgraph-omega-connector
export OMEGA_REPO=/path/to/omega-repo

cp "$CONNECTOR_REPO/upstream_patches/omega/api.yml.connector-overlay.yaml" \
   "$OMEGA_REPO/config/api.yml.connector-overlay.yaml"
cp "$CONNECTOR_REPO/upstream_patches/omega/env.required.txt" \
   "$OMEGA_REPO/config/env.required.txt"
```

### C. Что обновить в существующем `config/api.yml`

Сверить/привести к значениям:

1. `api.security.transport_mode: proxy_tls`
2. `api.security.require_https: true`
3. `api.auth.require_hmac: true`
4. `api.auth.hmac_secret_env: OMEGA_API_HMAC_SECRET`
5. `api.auth.hmac_headers`: `X-Signature`, `X-Timestamp`, `X-Nonce`
6. `api.limits.max_file_bytes: 20971520`

Reference:

- `upstream_patches/omega/INTEGRATION.md`

## PR Acceptance Quick Check

1. SGraph PR: код компилируется, hook вызывается в decrypt-flow.
2. Omega PR: config/env согласованы с connector auth/transport.
3. Connector repo: контракт неизменен (`contracts/openapi/connector-v1.yaml`).
4. E2E smoke: получаем `allow|quarantine|block` без fallback на happy path.
