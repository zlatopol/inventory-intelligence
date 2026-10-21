# ADR-0009: single multi-stage image. Stage 1 (Node) builds the SPA;
# stage 2 (Python) ships the API + built static files. Node, npm and
# node_modules stay OUT of the final image — same principle as not
# shipping a compiler to runtime.

# --- Stage 1: frontend build --------------------------------------------------
FROM node:22-slim AS frontend

WORKDIR /ui

# Dependency layer first — cached unless the lockfile changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# --- Stage 2: runtime ----------------------------------------------------------
FROM python:3.13-slim

# libgomp1: LightGBM's shared library needs the OpenMP runtime — absent
# from slim images (found the hard way: ModuleNotFoundError was only the
# first layer; ctypes raised OSError on the missing .so).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependency layer first — cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (pyproject is included for tooling metadata).
COPY pyproject.toml alembic.ini ./
COPY app/ app/
COPY migrations/ migrations/

# Built SPA + analytics images (served by FastAPI, ADR-0009).
COPY --from=frontend /ui/dist/ frontend/dist/
COPY docs/img/ docs/img/

# Migrations run at container start, then the API serves.
# Single-instance assumption: with N replicas racing `alembic upgrade`,
# move migrations to a separate one-shot job/init container.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
