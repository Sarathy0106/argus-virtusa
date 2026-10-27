.PHONY: help up down api web demo test redteam lint no-fakes gen-types clean install-web

PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
UVICORN ?= .venv/bin/uvicorn
PNPM ?= pnpm

API_HOST ?= 0.0.0.0
API_PORT ?= 8000

help:
	@echo "ARGUS v2 — Makefile Commands"
	@echo "  make up        - Boot the API (:8000) and the Next.js web app (:3000) together"
	@echo "  make api       - Run the FastAPI gateway only (:8000)"
	@echo "  make web       - Run the Next.js dev server only (:3000)"
	@echo "  make install-web - Install frontend dependencies (pnpm)"
	@echo "  make gen-types - Generate web/lib/types.generated.ts from the live OpenAPI"
	@echo "  make demo      - Run the end-to-end demo (Playwright) [added in R5]"
	@echo "  make test      - Run pytest backend tests"
	@echo "  make no-fakes  - Run the anti-fake CI gate (scripts/no_fakes.sh)"
	@echo "  make lint      - Ruff (backend) + next lint (frontend)"

# Boot API and web together. API runs in the background; web runs in the
# foreground (Ctrl-C stops web; the trap stops the API too).
up:
	@echo "Starting ARGUS v2 gateway on :$(API_PORT) and web on :3000 ..."
	@$(UVICORN) services.gateway.main:app --host $(API_HOST) --port $(API_PORT) & \
	API_PID=$$!; \
	trap "kill $$API_PID 2>/dev/null" EXIT INT TERM; \
	cd web && $(PNPM) dev

api:
	$(UVICORN) services.gateway.main:app --host $(API_HOST) --port $(API_PORT) --reload

web:
	cd web && $(PNPM) dev

install-web:
	cd web && $(PNPM) install

gen-types:
	cd web && $(PNPM) gen:types

down:
	docker compose -f deploy/docker-compose.yml down

# Full demo: boot API (:8000) + web (:3000), wait for health, run the Playwright
# demo twice, then tear down. Assumes `make install-web` + `pnpm build` were run.
demo:
	@echo "Booting gateway + web for the demo…"
	@$(UVICORN) services.gateway.main:app --host $(API_HOST) --port $(API_PORT) --log-level warning & \
	API_PID=$$!; \
	( cd web && $(PNPM) start ) & \
	WEB_PID=$$!; \
	trap "kill $$API_PID $$WEB_PID 2>/dev/null" EXIT INT TERM; \
	echo "Waiting for services…"; \
	for i in $$(seq 1 30); do \
	  curl -sf http://localhost:$(API_PORT)/health >/dev/null && \
	  curl -sf http://localhost:3000/ >/dev/null && break; \
	  sleep 1; \
	done; \
	cd web && $(PNPM) exec playwright test

test:
	$(PYTEST) tests/unit/ -v

redteam:
	$(PYTHON) -m tests.unit.test_redteam

no-fakes:
	bash scripts/no_fakes.sh

lint:
	.venv/bin/ruff check . && cd web && $(PNPM) lint

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
