.PHONY: help up down seed demo test redteam lint ui clean

PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest
STREAMLIT ?= .venv/bin/streamlit

help:
	@echo "ARGUS v2 — Makefile Commands"
	@echo "  make up       - Start local container stack (Postgres, Redis, OPA, etc.)"
	@echo "  make seed     - Generate reproducible synthetic datasets (seed=42)"
	@echo "  make test     - Run pytest unit and property tests"
	@echo "  make demo     - Execute end-to-end 5-minute CLI walkthrough demo"
	@echo "  make redteam  - Execute red-team prompt-injection and security suite"
	@echo "  make ui       - Launch Regulatory Mission Control Streamlit UI"
	@echo "  make lint     - Run code quality check (ruff)"

up:
	docker compose -f deploy/docker-compose.yml up -d

down:
	docker compose -f deploy/docker-compose.yml down

seed:
	$(PYTHON) scripts/gen_data.py --seed 42 --rows 100000

test:
	$(PYTEST) tests/unit/ -v

demo:
	$(PYTHON) scripts/demo_v2.py

redteam:
	$(PYTHON) -m tests.unit.test_redteam

ui:
	$(STREAMLIT) run ui/app.py --server.port 8501

lint:
	.venv/bin/ruff check .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
