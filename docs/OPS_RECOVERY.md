# Ops Recovery Runbook

Runbook для оперативного восстановления интеграции `connector -> omega` в локальном single-host окружении.

Рабочая директория:

```bash
cd <repo-root>/sgraph-omega-connector
```

## 1) Быстрый triage (2-3 минуты)

```bash
make health
make omega-logs
```

- Если `connector` и `sgraph_docs` = `ok`, а `omega` = `fail`, проблема локализована в `omega-api`.
- Если `omega` = `ok`, но в ответах много fallback `omega_timeout/omega_unavailable`, проверяем нагрузку и настройки workers/threads.

## 2) Чеклист `X -> Y`

| X (симптом) | Y (действие) |
|---|---|
| `omega: fail (The read operation timed out)` в `make health` | `make omega-restart` -> подождать 20-30 сек -> `make health` |
| В `connector` часто `reasons=["omega_timeout"]` | Увеличить `OMEGA_UVICORN_WORKERS` до `3` или `4` в `env/.env.local.example`, затем `make omega-restart` |
| После таймаутов сразу начинается `omega_unavailable` | Проверить `/omega/healthz`; если timeout -> `make omega-restart` |
| `omega_rejected_4xx` + `upstream_detail_code=invalid_file_base64` | Исправить входной payload на стороне отправителя (`file_base64`) |
| `omega_rejected_4xx` + `upstream_detail_code=extracted_text_too_large` | Ограничить `extracted_text` или отправлять файл вместо текста |
| `413 Request Entity Too Large` (HTML от nginx) | `make proxy-recreate` -> `make probe-body-limit` |
| После рестарта Omega долго не готов | Подождать до 60 сек и повторить `make health` |
| Под нагрузкой p95 растет и появляется fallback | Снизить нагрузку, оставить `OMEGA_OMP_NUM_THREADS=1`, `OMEGA_OPENBLAS_NUM_THREADS=1`, поднять workers |
| `make smoke` показывает только `quarantine` | Сначала восстановить `omega` (health), потом повторить smoke |
| Omega не восстанавливается > 5 минут | `make down` -> `make up` -> `make health` |

## 3) Команды восстановления

### A. Стандартное восстановление

```bash
make health
make omega-restart
make health
make smoke
```

### B. Точечная диагностика Omega

```bash
make omega-logs
curl -k -m 12 -sS -w "\nHTTP:%{http_code}\n" https://localhost:8088/omega/healthz
```

### C. Тюнинг runtime (single-host)

В `env/.env.local.example`:

```dotenv
OMEGA_UVICORN_WORKERS=3
OMEGA_OMP_NUM_THREADS=1
OMEGA_OPENBLAS_NUM_THREADS=1
```

Применение:

```bash
make omega-restart
make health
```

## 4) Сигналы, что нужно эскалировать

- `omega` регулярно падает в timeout даже на `healthz` после рестарта.
- Стабильно высокий fallback-rate на benign трафике.
- После `make down && make up` поведение не улучшается.

В этом случае собираем:

```bash
make omega-logs
make health
make smoke
```

И прикладываем вывод к инциденту.
