PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn

.PHONY: bootstrap run test test-unit test-integration test-contracts test-e2e-compose lint up up-no-build proxy-recreate omega-restart omega-logs down smoke smoke-upstream health preflight probe-body-limit perf-baseline perf-stress perf-report qualification-report qualify

bootstrap:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"

run:
	$(UVICORN) connector.app:create_app --factory --host 0.0.0.0 --port 18080 --reload

test: test-unit test-integration test-contracts

test-unit:
	$(PYTEST) -s tests/unit

test-integration:
	$(PYTEST) -s tests/integration

test-contracts:
	$(PYTEST) -s tests/e2e/test_openapi_contract.py

test-e2e-compose:
	RUN_COMPOSE_E2E=1 $(PYTEST) -s tests/e2e/test_compose_scenarios.py

lint:
	$(PYTHON) -m py_compile connector/*.py scripts/*.py tests/unit/*.py tests/integration/*.py tests/e2e/*.py

up:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml up --build -d

up-no-build:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml up -d

proxy-recreate:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml up -d --force-recreate reverse-proxy

omega-restart:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml up -d --force-recreate omega-api

omega-logs:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml logs --tail=200 omega-api

down:
	docker compose --env-file env/.env.local.example -f deploy/compose/docker-compose.local.yml down

smoke:
	$(VENV_PYTHON) -m scripts.smoke_local --base-url https://localhost:8088 --api-key local-connector-key --hmac-secret local-connector-hmac

smoke-upstream:
	$(VENV_PYTHON) -m scripts.e2e_sgraph_upstream_connector_path --base-url https://localhost:8088

health:
	$(VENV_PYTHON) -m scripts.compose_healthcheck --base-url https://localhost:8088

preflight:
	$(VENV_PYTHON) -m scripts.preflight_upstream --omega-base-url "$${OMEGA_BASE_URL:-https://reverse-proxy:8088/omega}"

probe-body-limit:
	mkdir -p artifacts/qualification
	$(VENV_PYTHON) -m scripts.e2e_connector_body_limit_probe --base-url https://localhost:8088 --api-key local-connector-key --hmac-secret local-connector-hmac --out artifacts/qualification/body_limit_probe_live.json

perf-baseline:
	@command -v k6 >/dev/null 2>&1 || (echo "k6 not found in PATH"; exit 2)
	mkdir -p artifacts/perf
	K6_BASE_URL=https://localhost:8088 K6_API_KEY=local-connector-key K6_HMAC_SECRET=local-connector-hmac K6_TLS_INSECURE=true \
		k6 run tests/perf/baseline.js --summary-export artifacts/perf/baseline-summary.json

perf-stress:
	@command -v k6 >/dev/null 2>&1 || (echo "k6 not found in PATH"; exit 2)
	mkdir -p artifacts/perf
	K6_BASE_URL=https://localhost:8088 K6_API_KEY=local-connector-key K6_HMAC_SECRET=local-connector-hmac K6_TLS_INSECURE=true \
		k6 run tests/perf/stress.js --summary-export artifacts/perf/stress-summary.json

perf-report:
	$(VENV_PYTHON) -m scripts.perf_report --baseline artifacts/perf/baseline-summary.json --stress artifacts/perf/stress-summary.json \
		--out-json artifacts/perf/perf-report.json --out-md artifacts/perf/perf-report.md

qualification-report:
	mkdir -p artifacts/qualification
	$(VENV_PYTHON) -m scripts.generate_qualification_report --base-url https://localhost:8088 --path /v1/scan/attachment \
		--api-key local-connector-key --hmac-secret local-connector-hmac --samples 100 --out-dir artifacts/qualification

qualify: preflight health test test-e2e-compose qualification-report
