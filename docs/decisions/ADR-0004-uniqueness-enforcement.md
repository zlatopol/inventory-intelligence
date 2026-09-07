# ADR-0004: Uniqueness enforcement — service check + DB constraint

- **Status**: accepted (2026-09-07)
- **Phase**: 1 — design

## Context

BR-2/BR-4: product/store names are unique case-insensitively. Possible guards:
a service-level lookup before insert, a repository-level lookup, a DB unique index.
Under concurrency (double submit), in-process checks race: two lookups may both see
"no duplicate" and both insert.

## Decision

**Service check + PostgreSQL unique index** (on `lower(name)`); repositories translate
the constraint violation into the same domain error the service check raises.
The repository-level pre-SELECT is **not** used: it adds a second racy check without
adding any guarantee the index does not already provide.

Roles:

- service check → deterministic, friendly rejection (EL-3: distinct message per rule);
- DB index → the guarantee under concurrency (last line of defense);
- repository → maps `UniqueViolation` to the domain "duplicate" error, so both paths
  produce one user-facing outcome.

## Alternatives considered

- DB-only (no service check) — rejected: raw constraint errors as the only rejection
  path make error messages non-deterministic and unfriendly.
- All three layers — rejected: the repository SELECT is redundant (see above).

## Consequences

- Two "duplicate" code paths must stay behaviorally identical — covered by API tests.
- The case-insensitive index shape (`UNIQUE INDEX ON product (lower(name))`) is a
  schema decision to be validated in `docs/database.md` and integration tests.
- Note: A-1 says a single actor, but double-submits and future second users make the
  index effectively free insurance.
