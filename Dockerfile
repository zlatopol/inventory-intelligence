FROM python:3.13-slim

WORKDIR /app

# Dependency layer first — cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (pyproject is included for tooling metadata).
COPY pyproject.toml alembic.ini ./
COPY app/ app/
COPY migrations/ migrations/

# Migrations run at container start, then the API serves.
# Single-instance assumption: with N replicas racing `alembic upgrade`,
# move migrations to a separate one-shot job/init container.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
