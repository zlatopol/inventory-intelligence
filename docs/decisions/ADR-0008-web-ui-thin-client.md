# ADR-0008: Web UI — a fourth door, thin client

- **Status**: accepted (2026-10-19)
- **Phase**: 4 — web UI
- **Origin**: instructor's oral requirement (Oct 2026, outside the методичка —
  recorded as EX-3 in requirements.md §8.1)

## Context

The system already has three doors to the same services: REST API, CLI menu,
tests. The instructor requires a full web UI for all operations (FR-1…FR-11,
EX-1, EX-2) — a working interface for the supply department employee instead
of the command line, plus an analytics tab showcasing the ML track.

The central risk of any UI: business rules drifting into the presentation
layer. The project's rules (BR-1…BR-8, D-1) live in services and are guarded
by 187 tests; a UI that re-implements validation would create a second source
of truth that will diverge.

## Decision

1. **The UI is a thin client over the REST API.** No business rule is
   implemented in the frontend. Forms send raw input; services validate.
2. **DomainError messages are relayed as-is.** The API already returns
   user-readable Russian messages with BR references (`detail`); the UI shows
   them in an error banner and keeps the form filled for correction.
   This works because EL-3 (one message per violated rule) was designed in
   Phase 0 — the UI requirement did not exist yet, but the discipline paid off.
3. **Re-fetch after every mutation** (no optimistic updates): the list state
   after a write is always the server's truth. Data volumes are educational;
   simplicity beats micro-optimizations.
4. **Honest simplifications**: no pagination, no authorization (single-actor
   system, A-1), no optimistic updates. Recorded rather than silently absent.

## Alternatives considered

- **UI-side validation layer** (validate before sending) — rejected: rule
  duplication; the classic «frontend says OK, backend says BR-2» divergence.
  Client-side checks are limited to mechanical ones (required fields,
  number parsing) that mirror CLI's `ask_int` philosophy.
- **UI talking to the database directly** — rejected: bypasses the service
  layer, transactions, and every guarantee the architecture is built on.
- **Read-only dashboard + forms in CLI** — rejected: instructor explicitly
  requires a full operational UI.

## Consequences

- The API surface is now a product contract consumed by a real client —
  API design decisions (status codes, error shape) are visible in the UI.
- `/api` prefix becomes necessary (UI routes vs API routes on one origin) —
  handled in ADR-0009.
- Architecture documentation gains a fourth door; `docs/architecture.md`
  updated accordingly.
- If a future rule is added, only services change; the UI displays the new
  message without redeployment.
