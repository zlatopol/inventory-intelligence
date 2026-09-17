# ADR-0006: Event history — one append-only table, snapshots instead of FKs

- **Status**: accepted (2026-09-17)
- **Phase**: 2 — ML extensions
- **Origin**: test-first (tests/integration/test_stock_events.py written before implementation)

## Context

`warehouse_quantity` / `store_product.quantity` are *state* (how much now). Demand
forecasting needs an *event stream* (how much moved, when). `docs/database.md §5`
reserved this decision; Phase 2 opens the ML track.

## Decision (Q1–Q3 fixed by the tests)

1. **One table** `stock_event` for both flows; `store_id IS NULL` marks receipts
   («неприменимо», not "unknown");
2. **`request_number` is a snapshot**, not an FK: an event is a witness of the past
   and must stay readable even if the referenced entity changes (EL-19 tradition);
3. **Append-only**: the repository exposes `add()` only; no update/delete paths,
   no `deleted_at` — events are eternal. No DB triggers (discipline + code review
   at this scale; reconsider if direct DB access ever appears).

Events ride the **same transaction** as the state change (receipt in FR-5,
shipment in FR-9): a rejected operation leaves no events (tested), a committed
one writes state+event atomically (ADR-0003 reuse).

## Alternatives considered

- Two tables (receipt_event / shipment_event) — rejected: one time-stream is
  simpler to query for datasets; the shared columns dominate.
- FK to store_request.id — rejected: mutable reference vs snapshot semantics.
- Writing events from an outbox/hook — rejected for now: YAGNI at this scale;
  service-level writes are explicit and testable.

## Consequences

- ML dataset reads one table ordered by `(occurred_at, product_id)` — index created.
- shipment events double as an audit trail of FR-9 processing.
- Future: read API for events (FR-12 candidate) + dataset builder on top.
