# ADR-0007: Day boundary — business timezone

- **Status**: accepted (2026-10-09)
- **Phase**: 3 — model as a service
- **Origin**: forecast slice known issue (forecast dates carried time-of-day)

## Context

`stock_event.occurred_at` stores a MOMENT (`timestamptz`, UTC) — correct for an
event journal. But the ML dataset contract (`app/ml/dataset.py`, Q1–Q3) operates
in DAYS: naive dates at midnight, one row per (pair, day), full grid with zeros.

The Phase 3 adapter `load_from_stock_event` violated the contract: it renamed
`occurred_at → date` and did nothing else. Timestamps with time-of-day reached
`build_features` / `build_training_table` (forecast dates carried time-of-day —
the visible symptom); day aggregation and zero-filling were silently absent
(a pair with two shipments a day would double-weight its days in rolling means).
The Kaggle adapter satisfied the contract for free (daily rows), and tests fed
clean synthetic loaders — only the production path was broken.

A day is a BUSINESS concept (a store's trading day), not a UTC interval.

## Decision

1. **Day boundary = business timezone** — `Settings.business_timezone`
   (default `Europe/Moscow`, overridable via env). The demand day of an event
   is its local calendar day:
   `tz_convert(business) → tz_localize(None) → normalize()`.
   Order matters: dropping the zone first would treat UTC as local time and
   lay the business night into "yesterday".
2. **The contract is restored at the adapter** (`load_from_stock_event`) —
   where it is declared (module docstring: «единый контракт выхода»).
   Consumers (`ForecastService`, evaluate scripts) must not pre-clean data;
   two service entry points (forecast/retrain) relying on a cleaning
   convention would be convention, not contract.
3. **Reuse over duplication**: the adapter delegates day aggregation and the
   zero-filled grid to `build_demand_dataset` (Phase 2, Q1–Q3, tested — the
   tz-localize scar already lives there). Filters `start/end` act on local
   days, inclusive.

## Alternatives considered

- **UTC day boundary** (just drop the zone) — rejected: 21:10 UTC =
  00:10 next day in Moscow; UTC midnight cuts the business evening and shifts
  night demand into "yesterday".
- **Store local naive timestamps in DB** — rejected: the event journal must
  store moments; presentation zones are a consumer choice (`timestamptz`
  semantics kept).
- **Normalize inside ForecastService** — rejected: every future consumer
  (CLI, monitoring) would have to remember to pre-clean; the written promise
  «adapters are interchangeable» would stay broken.

## Consequences

- Forecast dates are local midnights (known issue closed); recursive-horizon
  lags match training semantics (one row per pair-day).
- The day split depends on configuration: changing `business_timezone`
  re-slices history into days differently — acceptable (a day is a business
  notion); record the setting in MLflow run params when it matters.
- `submitted_at`/`processed_at` of store requests stay UTC in API output —
  out of scope; revisit if request-level analytics need local days.
- Seed stays valid: its 8–20 UTC window = 11–23 Moscow, one local day.
- Regression tests pin the contract on dirty timestamps (time-of-day,
  duplicate day, gap day, UTC→local boundary crossing) — the contract is
  guarded by tests, not by convention.
