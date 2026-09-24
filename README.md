# Inventory Intelligence Platform

Information system for the supply department of a wholesale warehouse — a portfolio
project built on top of an educational assignment (СПбГЭТУ «Технология
программирования», Тема 4).

- Requirements: `docs/requirements.md` (Phase 0 — complete)
- Architecture: `docs/architecture.md`, ADRs in `docs/decisions/`
- Database design: `docs/database.md`
- Progress log: `docs/project-status.md`

## Quick start

```bash
# 1. PostgreSQL (Docker)
docker compose up -d db

# 2. Python environment
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# 3. Migrations
.venv/bin/alembic upgrade head

# 4. Run the API
.venv/bin/uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Tests

```bash
docker compose up -d db   # integration/API tests need PostgreSQL
.venv/bin/pytest
```

## Demo

Full assignment scenario (FR-1 … FR-11) against a running API:

```bash
.venv/bin/uvicorn app.main:app --port 8000   # terminal 1
scripts/demo.sh                               # terminal 2
```

## Interactive menu (CLI)

The system can also be used interactively — the same services behind the third door:

```bash
.venv/bin/python -m app.cli
```

All 11 operations in Russian, human-readable domain errors (BR-rules referenced
in messages), exit with `0`.

## Full stack (Docker)

```bash
docker compose up --build -d    # api (migrations + uvicorn) + postgres
```
