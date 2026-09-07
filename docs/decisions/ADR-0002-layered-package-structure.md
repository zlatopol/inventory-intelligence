# ADR-0002: Package structure

- **Status**: accepted (2026-09-07); **редакция 2** (2026-09-07, same day) — decision
  reversed by the developer: domain-first instead of layer-first
- **Phase**: 1 — design

## Context

Two common layouts: layer-first (`api/`, `services/`, `repositories/`) vs
domain-first (`products/`, `stores/`, `requests/` — each with its own layers).
Three aggregates, one developer, learning project.

## Decision (редакция 2)

**Domain-first** packages — each domain module owns its layers:

```text
app/
├── products/        # router, service, repository, schemas, models
├── stores/          # router, service, repository, schemas, models
├── requests/        # router, service, repository, schemas, models (FR-8…FR-10)
├── shared/          # db session, config, base domain-error class
└── main.py          # app factory, router mounting
tests/
├── unit/
├── integration/
└── api/
```

Rationale (developer's): cheaper future scaling — a domain module is self-contained,
so extracting or handing off «products» later touches one folder, not four.

Cross-domain use cases (FR-9 lives in `requests/` and imports products/stores
repositories) are acceptable at this scale.

## Decision (редакция 1, superseded)

Layer-first chosen for top-to-bottom readability of one request's path.
Reversed the same day: the developer values module autonomy higher, and the
codebase is still empty — the cheapest possible moment to reverse.

## Consequences

- The module boundary replaces the folder boundary as the reading unit.
- `shared/` must stay free of domain logic; domain errors live in `shared` only as
  the base class, subtypes belong to their domains.

## Revisit trigger

None planned; extracting a domain into a service (ADR-0001 revisit) would start here.
