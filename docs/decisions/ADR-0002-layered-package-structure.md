# ADR-0002: Layered package structure

- **Status**: accepted (2026-09-07)
- **Phase**: 1 — design

## Context

Two common layouts: layer-first (`api/`, `services/`, `repositories/`) vs
domain-first (`products/`, `stores/`, `requests/` — each with its own layers).
Three aggregates, one developer, learning project.

## Decision

**Layer-first** packages: `app/api`, `app/services`, `app/repositories`, `app/models`,
`app/schemas`, `app/core`.

Rationale: the execution path of one request is readable top-to-bottom in the tree
(API → service → repository), which matches how the project is learned and reviewed.
At three aggregates the domain-first benefit (module autonomy) is not yet needed.

## Alternatives considered

Domain-first — deferred: better module encapsulation and cheaper extraction of a
bounded context, but scatters one use case across folders at this scale.

## Consequences

- Use cases touching several aggregates (FR-9: warehouse + store + request) import
  several repositories into one service — acceptable now.
- Folder moves are a cheap refactor while the codebase is small.

## Revisit trigger

When `services/` or `repositories/` grows enough that related files stop being
recognizable at a glance (est. > ~8–10 files per folder), or a second developer joins.
