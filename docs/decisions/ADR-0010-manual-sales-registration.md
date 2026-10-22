# ADR-0010: Manual sales registration

- **Status:** Accepted for the first implementation
- **Decision date:** 2026-10-22
- **Scope:** Manual registration of store sales and reversal of incorrectly registered sales
- **Implementation status:** Not implemented; this document records agreed requirements and design decisions

## Context

The application already supports warehouse stock, store requests, processing requests, and per-store stock. Processing a request moves goods from the warehouse to a store. The next functional increment is manual registration of sales, which reduces a store's stock.

The feature must fit the existing modular-monolith architecture and inventory history. The first version should remain deliberately small: no POS integration, bulk daily import, weight-based quantities, new role system, or separate sales-detail page.

This is a project extension, not one of the original operations in the educational assignment. Keep it documented separately from the original requirements.

## Decisions

### 1. Data and domain model

1. A sale is recorded as a `sale` event in the existing stock-movement/history model. Do not introduce a separate sale entity for the first version.
2. One registration represents one product, one store, and one quantity.
3. A successful sale reduces the current quantity of that product in that store.
4. Sale creation and stock deduction must be atomic: both commit, or neither does.
5. A store's stock must never become negative.
6. A sale must remain part of the inventory event history.
7. Use the existing application access model. Do not add roles, responsibility levels, or a separate authorization system specifically for sales.
8. The current repository/database design must be inspected during implementation to reconcile this decision with older documentation that describes event history as a future extension. Reuse the existing model where available; do not create a parallel history model without a demonstrated need.

### 2. Quantity validation

1. Quantity must be a positive integer.
2. Zero, negative, and fractional quantities are rejected.
3. A sale cannot exceed the currently available quantity in the selected store.
4. Validation must exist on the backend, not only in the UI.
5. The UI displays the full product assortment for the selected store and each product's current stock.
6. Products with zero stock remain visible, but a sale cannot be registered for them.
7. If stock is insufficient for the requested quantity, the operation is rejected with a clear error and, where practical, the current available quantity.

Weight-based products and fractional quantities are explicitly out of scope for the first version.

### 3. Dates and timestamps

1. `sold_at` represents the actual date and time of the sale.
2. `created_at` represents when the sale was registered in the system and is assigned automatically.
3. Sales may be registered retrospectively; `sold_at` can be in the past.
4. The two timestamps serve different purposes and must not be conflated.
5. The allowed treatment of a future `sold_at` value was not decided in this discussion and must not be silently assumed.

### 4. Duplicate requests and concurrency

1. Retrying the same request must not deduct stock twice.
2. Concurrent sale attempts must be safe. The backend/database must ensure that successful sales cannot collectively exceed available stock.
3. For example, if a store has 5 units and two concurrent requests each attempt to sell 4, at most one may succeed.
4. Stock validation, stock mutation, and event creation must be coordinated transactionally.
5. The concrete idempotency mechanism/API contract is not yet selected. Choose it during API design and test it explicitly; the requirement itself is accepted.

### 5. Reversing a sale

1. An incorrectly registered sale is reversed by creating a compensating `sale_reversal` event; the original sale is not edited or deleted.
2. A reversal must reference the original sale so that the two operations can be traced to each other.
3. Reversal returns the sold quantity to the store's **current** stock, regardless of later movements. It does not reconstruct or rewrite historical stock balances.
4. Reversal creation and the stock increase must be atomic.
5. A sale may be reversed only once. Duplicate reversal attempts must not return stock twice.
6. The reversal does not require a reason in the first version.
7. Reversal is available under the existing access model; no new roles are introduced.
8. The UI asks for confirmation before reversing a sale. The dialog identifies the store, product, and quantity and explains that the quantity will be returned to current stock.
9. A reversal is itself retained in history and linked to the original sale. The original sale remains visible with a cancelled/reversed status in the UI.

### 6. Sales UI

Add a separate **Sales** tab; do not mix sale registration into store-request processing.

The tab contains:

- A registration form with store, product, positive integer quantity, and sale date.
- The full assortment for the selected store, with current stock displayed and sale disabled when stock is zero.
- A sales-history table containing active and reversed/cancelled sales.
- Filters by store, product, date, and status: all, active, cancelled.
- A reversal action for active sales, protected by a confirmation dialog.

Registration is one click after completing the form; no additional confirmation dialog is required. On success, show a clear message (for example, “Sale registered”) and reset the form to reduce accidental duplicate submissions. On failure, show a clear explanation and do not imply that the sale was recorded.

A separate sale-details page is not part of the first version. The history table is sufficient.

### 7. Testing and correctness

The implementation must include appropriate unit, PostgreSQL integration, and API/UI tests for the relevant layers. At minimum, cover:

- successful sale decreases store stock and creates a `sale` event;
- positive-integer validation, including zero, negative, and fractional inputs;
- insufficient stock and zero stock;
- sale event and stock update roll back together on failure;
- repeated submission does not cause a second deduction;
- concurrent requests cannot oversell stock;
- past-dated sale preserves both `sold_at` and `created_at`;
- reversal adds the quantity to current stock and creates a linked `sale_reversal` event;
- reversal still works after later stock movements;
- repeated reversal does not return stock twice;
- failure during reversal does not leave a partial update;
- UI history includes reversed sales, filters work, and reversal requires confirmation.

All schema changes must use Alembic migrations, consistent with the repository's existing database policy.

## Alternatives discussed and rejected for the first version

| Topic | Chosen option | Alternative not chosen now | Reason |
|---|---|---|---|
| Sale persistence | `sale` event in existing stock-movement history | Separate sale entity | Preserve one consistent history and avoid unnecessary parallel data models |
| Incorrect sale | Compensating `sale_reversal` event | Edit/delete original sale | Preserve an auditable history |
| Quantity | Positive integers only | Fractional quantities | Keep the first version simple; weight-based items are a future idea |
| Sale date | Allow retrospective entry | Restrict to today | Staff can enter a sale that was missed earlier |
| Cancellation reason | Not required | Mandatory reason | Avoid extra workflow complexity |
| Access control | Existing access model | New roles/responsibility levels | Not currently needed |
| UI layout | Separate Sales tab with history table | Separate details page | Avoid overloading the interface |
| Registration confirmation | One-click submission | Extra confirmation dialog | Keep normal entry fast |
| Reversal confirmation | Required | Immediate reversal | Reduce accidental stock returns |
| Assortment | Show all store products, including zero-stock items | Hide zero-stock products | Keep the full assortment visible and explain availability |

## Future ideas (not part of the first version)

- Bulk daily sales entry: one store, one date, multiple products and quantities.
- Weight-based products and fractional quantities with units such as kilograms or litres.
- Roles and more granular responsibility/access controls.
- Optional reason for reversing a sale.
- A dedicated sale-details page, if the history table becomes insufficient.
- POS integration and CSV/Excel import, if later needed.

These are ideas only, not commitments or first-version acceptance criteria.

## Open implementation details

The following are deliberately left for implementation design rather than treated as already decided:

- The exact idempotency mechanism and API contract for retry-safe requests.
- The precise mapping to the current stock-movement model after inspecting the existing code and migrations.
- Whether future-dated `sold_at` values are allowed.
- Exact endpoint names, response schemas, database column layout, and UI component structure.

Any implementation choice must preserve the accepted behavior above and should not introduce unnecessary complexity.

## Acceptance summary

The feature is ready for implementation only when a staff member can manually register one product sale for one store, the stock update and history event are atomic and concurrency-safe, a mistaken sale can be reversed exactly once without deleting history, and the Sales tab provides a clear registration flow and a filterable history of active and reversed sales.
