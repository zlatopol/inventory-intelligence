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
