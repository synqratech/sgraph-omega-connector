# Open Source Publishing Guide

Цель: зафиксировать, что публикуем в open source, а что оставляем только для внутренней работы.

Важно: этот документ описывает подготовку. Он не выполняет чистку автоматически.

## 1) Рекомендуемые профили публикации

### Профиль A (рекомендуемый): "Core OSS"
- Публикуем только то, что нужно внешнему пользователю для запуска connector и понимания контракта.
- Внутренние квалификационные артефакты, локальные env/venv, внутренние patch-инструкции не публикуем.

### Профиль B: "Extended OSS"
- Всё из Profile A.
- Плюс тесты и утилиты, если хотите показать полный QA/perf-пайплайн.

## 2) Матрица по папкам

| Папка/файл | Статус для OSS | Комментарий |
|---|---|---|
| `connector/` | Keep | Основной runtime-код сервиса. |
| `contracts/openapi/` | Keep | Публичный API-контракт, обязателен. |
| `contracts/schemas/` | Keep | Примеры payload и schema snapshots. |
| `deploy/compose/` | Keep (sanitize) | Локальный compose полезен, но убрать жёсткие привязки к локальным путям/внутренним repo names при необходимости. |
| `deploy/proxy/` | Keep | Прокси/TLS слой важен для воспроизводимости. |
| `deploy/omega/` | Keep | Dockerfile для стабильного local runtime. |
| `env/.env.example` | Keep | Публичный template с плейсхолдерами. |
| `env/.env.cloud.example` | Keep | Полезно для production-like примера. |
| `env/.env.local.example` | Optional (sanitize) | Можно оставить, но проверить dev-значения/локальные токены. |
| `tests/unit`, `tests/integration`, `tests/e2e/test_openapi_contract.py` | Keep | Полезно и безопасно для OSS. |
| `tests/perf/` | Optional | Оставлять, если хотите публично поддерживать perf-набор. |
| `scripts/` | Keep (selective) | Оставлять только универсальные скрипты (smoke/health/signature/preflight). |
| `scripts/*qualification*`, отчётные генераторы | Optional/Internal | Для OSS не обязательны, особенно если завязаны на внутренний процесс. |
| `docs/CONTRACT.md` | Keep | Публичная спецификация поведения. |
| `docs/CONTRACT_CHANGE_POLICY.md` | Keep | Политика изменений контракта. |
| `docs/OPS_RECOVERY.md` | Keep (sanitize) | Убрать absolute paths и внутренние формулировки. |
| `README.md` | Keep (sanitize) | Убрать absolute filesystem paths и внутренние ссылки. |
| `CHANGELOG.md` | Keep | Важно для прозрачности изменений. |
| `upstream_patches/` | Optional/Internal | Сильно внутренний контекст (названия внутренних репо, абсолютные пути, PR-чеклисты). Для OSS обычно убрать или санитизировать в generic integration notes. |
| `artifacts/` | Exclude | Временные отчёты, live-результаты, шум. Не публиковать. |
| `.venv/`, `.venv-win/`, `.pytest_cache/`, `__pycache__/`, `*.egg-info/` | Exclude | Локальные build/runtime артефакты. |

## 3) Что точно НЕ публиковать

- Любые локальные/временные артефакты:
  - `artifacts/**`
  - `.venv/**`, `.venv-win/**`, `.pytest_cache/**`, `**/__pycache__/**`
  - `sgraph_omega_connector.egg-info/**`
- Внутренние абсолютные пути вида `/mnt/d/...`
- Внутренние названия/топология приватных репозиториев, если не хотите их раскрывать
- Реальные секреты/токены/ключи (включая "временные dev", если они где-то используются в бою)

## 4) Документы: что оставить, что санитизировать

### Оставить
- `README.md`
- `CHANGELOG.md`
- `docs/CONTRACT.md`
- `docs/CONTRACT_CHANGE_POLICY.md`
- `docs/OPEN_SOURCE_PUBLISHING_GUIDE.md` (этот файл)

### Санитизировать перед публикацией
- `README.md`, `docs/OPS_RECOVERY.md`:
  - заменить абсолютные пути на относительные;
  - убрать ссылки на внутренние workspace-пути;
  - привести команды к универсальному виду.
- `upstream_patches/*`:
  - либо убрать полностью;
  - либо заменить на generic docs без упоминания внутренних репозиториев/путей.

## 5) Pre-publish checklist (обязательно)

1. Удалить/исключить runtime artifacts:
   - `artifacts/`, `.venv*/`, `.pytest_cache/`, `*.egg-info/`, `__pycache__/`.
2. Проверить, что нет абсолютных путей:
   - поиск `/mnt/d/`, `C:\`, `file://`.
3. Проверить, что нет явных dev-токенов/ключей:
   - `dev-local-token`, `local-connector-key`, `dev-api-key` (допустимо только как явно помеченные примеры).
4. Проверить docs на внутренние ссылки и формулировки.
5. Запустить базовые проверки:
   - `make test`
   - `make smoke` (или эквивалент)
6. Проверить итоговый состав репозитория глазами внешнего пользователя:
   - понятный `README`
   - контракт и примеры
   - минимальный reproducible local run.

## 6) Минимальный рекомендуемый состав OSS-репозитория

- `LICENSE`
- `CONTRIBUTING.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`
- `connector/`
- `contracts/`
- `deploy/`
- `env/.env.example`
- `env/.env.cloud.example`
- `tests/` (минимум unit/integration/contract)
- `scripts/` (минимальный набор)
- `README.md`
- `CHANGELOG.md`
- `.github/ISSUE_TEMPLATE/*`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/ci.yml`
- `docs/CONTRACT.md`
- `docs/CONTRACT_CHANGE_POLICY.md`

Остальное — по ситуации после sanitization.
