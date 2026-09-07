# ADR-0005: Soft delete + plain FKs (no snapshots)

- **Status**: accepted (2026-09-07)
- **Phase**: 1 — design

## Context

BR-8 allows deleting a store that has only *processed* requests; EL-19 requires those
requests to keep referencing the store readably. FR-2/BR-3 allow deleting products.
Processed requests reference **both** entities. The project also treats history as a
first-class asset (future ML forecasting needs intact event history).

## Decision

1. **Soft delete** for product and store: a `deleted_at TIMESTAMPTZ` column; NULL = live.
   The application never issues physical DELETEs.
2. **Plain FKs** (default RESTRICT) from store_request and store_product. Since physical
   DELETE never happens, RESTRICT never fires — no `ON DELETE` options, no name-snapshot
   columns needed; joins always resolve names.
3. Uniqueness (BR-2/BR-4) enforced by **partial unique indexes** over live rows only.

## Alternatives considered

- Hard delete + `ON DELETE SET NULL` + name snapshots — rejected: snapshots duplicate
  data, SET NULL loses the reference, history is destroyed.
- Hard delete + `ON DELETE CASCADE` — rejected: silently erases request history
  (violates EL-19 and the ML-history constraint).
- Hard delete + RESTRICT — rejected: contradicts BR-8 (processed requests must not block
  store deletion).

## Consequences

- Two recurring taxes, accepted knowingly: (1) every list read must filter
  `deleted_at IS NULL`; (2) uniqueness indexes must be partial. Both are covered by
  integration tests.
- BR-3/BR-8 semantics unchanged: guards check conditions *before* the soft delete.
- A soft-deleted name can be re-created as a new live row (history keeps both spellings).
- Design review spawned **OP-3**: BR-3 checks warehouse quantity only, while store rows
  may still hold the product — to be resolved at the requirements level.
