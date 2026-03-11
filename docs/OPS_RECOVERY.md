# Ops Recovery Runbook

Runbook for оперативный recovery of the `connector -> omega` integration in a local single-host environment.

Working directory:

```bash
cd <repo-root>/sgraph-omega-connector
````

## 1) Quick triage (2–3 minutes)

```bash
make health
make omega-logs
```

* If `connector` and `sgraph_docs` = `ok`, but `omega` = `fail`, the issue is localized in `omega-api`.
* If `omega` = `ok`, but responses contain many `omega_timeout/omega_unavailable` fallbacks, check load and the workers/threads settings.

## 2) `X -> Y` checklist

| X (symptom)                                                            | Y (action)                                                                                                |
| ---------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| `omega: fail (The read operation timed out)` in `make health`          | `make omega-restart` -> wait 20–30 sec -> `make health`                                                   |
| `reasons=["omega_timeout"]` appears frequently in `connector`          | Increase `OMEGA_UVICORN_WORKERS` to `3` or `4` in `env/.env.local.example`, then run `make omega-restart` |
| `omega_unavailable` starts immediately after timeouts                  | Check `/omega/healthz`; if it times out -> `make omega-restart`                                           |
| `omega_rejected_4xx` + `upstream_detail_code=invalid_file_base64`      | Fix the input payload on the sender side (`file_base64`)                                                  |
| `omega_rejected_4xx` + `upstream_detail_code=extracted_text_too_large` | Limit `extracted_text` or send a file instead of text                                                     |
| `413 Request Entity Too Large` (HTML from nginx)                       | `make proxy-recreate` -> `make probe-body-limit`                                                          |
| Omega takes a long time to become ready after restart                  | Wait up to 60 sec and run `make health` again                                                             |
| Under load, p95 increases and fallback appears                         | Reduce the load, keep `OMEGA_OMP_NUM_THREADS=1`, `OMEGA_OPENBLAS_NUM_THREADS=1`, increase workers         |
| `make smoke` shows only `quarantine`                                   | First recover `omega` (health), then rerun smoke                                                          |
| Omega does not recover for more than 5 minutes                         | `make down` -> `make up` -> `make health`                                                                 |

## 3) Recovery commands

### A. Standard recovery

```bash
make health
make omega-restart
make health
make smoke
```

### B. Targeted Omega diagnostics

```bash
make omega-logs
curl -k -m 12 -sS -w "\nHTTP:%{http_code}\n" https://localhost:8088/omega/healthz
```

### C. Runtime tuning (single-host)

In `env/.env.local.example`:

```dotenv
OMEGA_UVICORN_WORKERS=3
OMEGA_OMP_NUM_THREADS=1
OMEGA_OPENBLAS_NUM_THREADS=1
```

Apply changes:

```bash
make omega-restart
make health
```

## 4) Signals that escalation is needed

* `omega` keeps timing out regularly even on `healthz` after restart.
* Consistently high fallback rate on benign traffic.
* Behavior does not improve after `make down && make up`.

In this case, collect:

```bash
make omega-logs
make health
make smoke
```

And attach the output to the incident.
