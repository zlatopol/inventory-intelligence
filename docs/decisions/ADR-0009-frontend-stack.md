# ADR-0009: Frontend stack — React + TypeScript + Vite, served by FastAPI

- **Status**: accepted (2026-10-19)
- **Phase**: 4 — web UI
- **Origin**: EX-3 design discussion (stages 1–6, 2026-10-13…19)

## Context

EX-3 needs a rendering technology. Constraints: full CRUD UI + 2 charts +
analytics tab; the developer's track is ML engineering (frontend is not the
competence being built, but is a declared learning interest); the project
philosophy is «complexity only with justification» (ADR-0001).

Two viable families: server-side templates (Jinja2, optionally + htmx) —
zero new toolchain; SPA (React/Vue) — a second toolchain (node, npm, Vite)
and weeks of learning curve, but the developer explicitly chose the learning
goal («большую часть кода пишешь ты, а я смотрю и пытаюсь понять»).

## Decision

1. **React 18 + TypeScript + Vite SPA** in `frontend/`. Learning goal is the
   primary justification — recorded honestly. TypeScript mirrors the
   project's typing culture (type hints, Pydantic): API shape mismatches
   surface at compile time, not in the browser.
2. **API moves under `/api`** (breaking change, covered by the existing test
   suite). SPA routes live in the root; conflict between `/products` (JSON)
   and `/products` (page) is resolved by namespace — the industry norm.
3. **No CORS anywhere.** Dev: Vite dev-server proxies `/api/*` to
   `127.0.0.1:8000` — same origin from the browser's point of view.
   Prod: FastAPI serves the built SPA itself — one origin. CORSMiddleware
   would be configuration for a problem we do not have.
4. **FastAPI serves the built SPA**: `StaticFiles` at `frontend/dist` with
   an SPA fallback to `index.html` (mounted LAST — `/docs`, `/openapi.json`,
   `/api/*` keep working). Analytics images: `/img` → `docs/img` — single
   source of truth (a regenerated chart reaches the UI without copying).
5. **Single multi-stage Docker image**: stage 1 — Node 22, `npm ci`,
   `vite build`; stage 2 — Python 3.13 + `dist/` + `docs/img`. No nginx
   container: no TLS termination, no replicas — nothing to justify it.
6. **Deliberate simplifications**: hand-written TS types mirroring Pydantic
   schemas (~10 interfaces; openapi-generator is overkill — future idea);
   plain `fetch` in hooks (no TanStack Query); react-router for routes;
   Chart.js + react-chartjs-2 for the forecast chart (fact + forecast
   series, dashed line for baseline — honesty made visible); no
   ESLint/Prettier (`tsc` in build is the gate; a third toolchain for ~30
   files is not justified).

## Alternatives considered

- **Jinja2 (+ htmx)** — the engineering-minimal choice (~×1 effort, zero new
  toolchain, testable with the existing TestClient infrastructure). Chosen
  against for the learning goal; would be the recommendation for a pure
  portfolio-efficiency objective.
- **Vue 3** — gentler learning curve, but React knowledge is more
  transferable; the project's typing culture pairs better with TS+React.
- **Separate nginx container** — closer to production topology, but adds a
  service and config we have no requirements for; recorded as the scaling
  answer («nginx in front, static to CDN») instead.
- **HashRouter (no /api move)** — zero backend changes, but `/#/products`
  URLs are a 2010s smell; the /api move is a one-time cost covered by tests.
- **Generated TS types from openapi.json** — attractive at scale; for ~10
  stable interfaces the generator adds a build step and drift risk of its own.

## Consequences

- The repository gains a second toolchain (node/npm, `frontend/package.json`,
  lockfile). CI gains a parallel `frontend` job (Node 22: `npm ci` →
  `npm run build` → `npm test`); no Postgres needed there.
- The `/api` move is breaking: `app/main.py`, all API tests, `demo.sh`,
  README updated in one commit (187 tests guard the move).
- Dev workflow: two terminals (uvicorn + `npm run dev` on :5173);
  prod workflow unchanged for the user (`docker compose up` → :8000 now
  serves both API and UI).
- Frontend tests: Vitest + React Testing Library (~15 tests: API client
  error mapping, page behavior with mocked fetch, status badges, baseline
  dashed-line logic). Chart pixels and CSS are not tested — library
  responsibility, recorded here.
