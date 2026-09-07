# ADR-0001: Modular monolith

- **Status**: accepted (2026-09-07)
- **Phase**: 1 — design

## Context

Phase 0 produced 10 operations for a single-actor domain (A-1: one supply-department
employee; A-2: one warehouse). The project is a learning/portfolio system with one
developer and no throughput requirements.

## Decision

Build a **single deployable application + single PostgreSQL database** (modular monolith).
No microservices, no message broker, no distributed transactions.

## Alternatives considered

- Microservices — rejected: operational cost (deployment, network failure modes,
  cross-service consistency) with zero benefit at this scale.
- Event-driven architecture — rejected: no async workflow exists in the requirements;
  would add infrastructure before any problem demands it.

## Consequences

- One codebase, one migration chain, local transactions — simplest correctness story.
- The layered structure (ADR-0002) keeps the option of extracting modules later cheap:
  boundaries are already interfaces (service/repository).

## Revisit trigger

Sustained independent scaling needs of components, or a team split — neither exists.
