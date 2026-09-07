# Architecture

> Phase 1 — design document. Grounded in `docs/requirements.md` (Phase 0, complete).
> Status: draft v1 (2026-09-07). Decisions are recorded as ADRs in `docs/decisions/`.

## 1. System shape

**Modular monolith**: a single deployable Python application + a single PostgreSQL
database. No microservices, no message brokers, no distributed coordination — the
domain (10 operations, one actor, one warehouse) does not justify the operational cost.

- ADR-0001 — Modular monolith
- ADR-0002 — Layered package structure
- ADR-0003 — Transaction boundary in services
- ADR-0004 — Uniqueness enforcement (service + DB constraint)

## 2. Layers and rules

```text
API (FastAPI routers, Pydantic schemas)
 ↓
Service / Application (business rules BR-1…BR-8, use-case orchestration, transactions)
 ↓
Repository / Data Access (SQLAlchemy queries; one aggregate per repository)
 ↓
PostgreSQL (source of truth; constraints and indexes as the last line of defense)
```

Rules:

1. Dependencies point **down only**. A service must not import FastAPI; a repository
   must not know about HTTP.
2. **Business logic lives in services**, never in route handlers. A handler validates
   the *format* of input (Pydantic) and translates domain outcomes into HTTP responses.
3. **Repositories make no business decisions**: the service decides *when/why*,
   the repository knows *how* to read/write.
4. **Transactions are owned by services** (ADR-0003): a use case spanning several
   aggregates (FR-9: warehouse −N, store +N, request status) opens one transaction
   and calls the repositories inside it.
5. **Domain errors** (per EL-3/EL-7/EL-8/EL-18: «товар не найден», «дубликат»,
   «заявка уже обработана», …) are raised by services as typed exceptions; the API
   layer maps them to HTTP 4xx with a message per violated rule. Error *texts* are not
   normative (EL-3), distinctness is.

## 3. Technology stack

| Concern | Choice | Notes |
|---|---|---|
| Language | Python 3.12+ | project target |
| Web framework | FastAPI | handlers thin; OpenAPI for free |
| Validation | Pydantic v2 | request/response schemas at the API edge |
| ORM | SQLAlchemy 2.x | repositories own all queries |
| Migrations | Alembic | schema changes never applied manually |
| Database | PostgreSQL 16 | source of truth; case-insensitive unique indexes |
| Testing | pytest | unit (services) / integration (repositories, real PG) / API (httpx) |
| Runtime env | Docker Compose | local PostgreSQL; app container later |

## 4. Package structure (ADR-0002, ред. 2 — domain-first)

Domain-first (reversed from layer-first on the developer's call, 2026-09-07):
each domain module owns its layers.

```text
app/
├── products/       # router.py, service.py, repository.py, schemas.py, models.py
├── stores/         # same layout
├── requests/       # same layout (FR-8…FR-10; FR-9 service imports products/stores repos)
├── shared/         # config, db session, base domain-error class
└── main.py         # app factory, router mounting
tests/
├── unit/           # service tests (BR logic, no DB)
├── integration/    # repository tests against real PostgreSQL
└── api/            # endpoint tests (validation, error mapping)
```

## 5. Vertical slices (implementation order)

Each slice goes end-to-end: migration → model → repository → service → API → tests.

| Slice | Scope | Requirements covered |
|---|---|---|
| 1. Products | warehouse list CRUD + receipt + warehouse view | FR-1, FR-2, FR-5, FR-6 (BR-1, BR-2, BR-3, BR-5) |
| 2. Stores | store list CRUD | FR-3, FR-4 (BR-1, BR-4, BR-8) |
| 3. Requests | submit / process / view requests | FR-8, FR-9, FR-10 (BR-6, BR-7; atomicity ADR-0003) |
| 4. Per-store view | products by stores | FR-7 |

Slice 1 first: it exercises every layer once on the simplest aggregate, establishing
all patterns (error mapping, transaction handling, migration flow) that slices 2–4 reuse.

## 6. Error-handling flow (example: FR-1)

```text
POST /products  {"name": "  молоко  "}
  → API: Pydantic validates the payload shape (name: str)
  → Service: trims (D-1), checks BR-1 (non-empty) → DomainError("empty name")
             checks BR-2 via repository lookup → DomainError("duplicate name")
             on insert: catches unique-violation (translated by repository) → same error
  → API: maps DomainError subtype → HTTP 4xx + message; success → 201 + product
```

Two sources, one outcome: the service check gives a friendly deterministic rejection;
the DB index is the guarantee under concurrency (ADR-0004).

## 7. Testing strategy (per layer)

- **Unit (services)**: BR logic, D-1 processing, use-case ordering — repositories faked.
- **Integration (repositories)**: real PostgreSQL (Docker Compose), including the
  uniqueness race behavior (insert-then-insert → constraint violation).
- **API**: httpx against the app; validation errors, domain-error → HTTP mapping,
  success shapes.
- **ML note (future)**: FR-8/FR-9 event data (submission/processing dates) is the
  future forecasting history; preserving it is a design constraint, not an afterthought.
