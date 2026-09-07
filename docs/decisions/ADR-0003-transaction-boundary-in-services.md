# ADR-0003: Transaction boundary in services

- **Status**: accepted (2026-09-07)
- **Phase**: 1 — design

## Context

FR-9 requires atomicity: warehouse quantity −N, store quantity +N, request status
→ «обработана» — «все или ничего» (EL-17). Three different aggregates are modified
by one use case.

## Decision

**Services own transaction boundaries.** A service opens the transaction (unit of
work) and calls the repositories it needs inside it; repositories never begin or
commit transactions themselves.

Rationale: a transaction is a property of a *use case*, not of a *table*. No single
repository owns all three FR-9 changes; if a repository opened the transaction, it
would have to know about the other aggregates — breaking the one-aggregate-per-repository
boundary.

## Alternatives considered

- Repository-level transactions — rejected: cannot span multiple repositories without
  cross-repository knowledge.
- API-layer transactions — rejected: HTTP concerns (status mapping, retries) must not
  own data consistency.

## Consequences

- Repositories are composable inside a use case; the same repositories work in
  non-transactional reads.
- Services need a session/unit-of-work abstraction (provided by `app/core/db`).
- Integration tests must verify the rollback path (e.g., BR-7 failure after the
  store-side update attempt leaves all three values unchanged).
