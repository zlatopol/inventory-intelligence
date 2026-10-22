# Project Status

Last updated: 2026-10-22

## Current phase

**Phase 4 — Web UI (EX-3): COMPLETE (2026-10-22).** Steps 0–13 done; UI polish, screenshots, and retrospective recorded below.

**Phase 3 — Model as a service: COMPLETE** (forecast/retrain API, CLI 12,
holiday features, blocked horizon evaluation, replenishment EX-2 — записи ниже;
отдельной ретроспективы не было: уроки зафиксированы внутри срезов).

**Phase 2 — Extensions toward ML: COMPLETE (2026-10-08, v0.2.0).** Event history,
CI, Docker, seed, dataset contracts, baselines, MLflow, Kaggle stage, LightGBM
(full 500 pairs: MAE 6.01 / WAPE 11.5%, baseline beaten by 21.6%). See the
PHASE 2 section below.

**Phase 1 — Design & Implementation: COMPLETE (2026-09-15).** architecture.md + ADR-0001…0005;
11/11 FR implemented end-to-end (4 slices, domain-first packages); 4 migrations;
89 tests (unit/integration/api against real PostgreSQL); live demo `scripts/demo.sh`;
retrospective recorded below.

**Phase 0 — Requirements formalization: COMPLETE (2026-09-07).** All 10 operations
accepted (7 original + 3 derived), 8 BR, 3 A, 1 D, 21 EL, both OP closed; integrity
check passed. Historical scope note: Phase 0 covered original + derived assignment
requirements only — no PostgreSQL, SQLAlchemy, FastAPI, Docker, ML, DB tables,
architecture, or API design.

## Process (agreed)

Mentor Mode, iterative FR-by-FR:

> mentor asks clarifying questions → developer formulates FR → mentor reviews (unambiguous? verifiable? nothing added? nothing lost?) → iterate until agreed → next FR.

FR order:

1. FR-1 — add product («включить новый товар в список товаров на складе»)
2. FR-2 — remove product («удалить ненужный товар из складского списка»)
3. FR-3 — add store («включить новый магазин в список магазинов»)
4. FR-4 — remove store («удалить ненужный магазин из списка»)
5. FR-5 — record goods receipt («учесть поступление некоторого товара на склад»)
6. FR-6 — view warehouse stock («просмотреть информацию о товарах на складе»)
7. FR-7 — view stock by stores («просмотреть информацию о товарах по магазинам»)

Store requests («заявки магазинов на текущий год») are discussed **separately after FR-7**: present in the domain description but not among the seven operations.

## Requirements source

Primary source: `docs/source/ТРПО_КР.doc` (методические указания СПбГЭТУ «Технология программирования», В.Л. Литвинов), **Тема 4** «Информационная система СНАБЖЕНИЕ отдела снабжения оптовой базы».

Discipline: original assignment requirements are kept **separate** from project extensions and future ideas. Nothing outside the методичка may be presented as an original requirement.

## FR-1: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md` (Sections 4–7): D-1, BR-1, BR-2, FR-1 and elaborations EL-1…EL-5.

Agreed decisions (Q1–Q11):

- **Q1**: input = name only; quantity starts at `0`; quantity changes belong to FR-5 («учесть поступление»);
- **Q2**: duplicates rejected → name is the unique product identifier in the warehouse list;
- **Q3**: postcondition = product appears in the warehouse list; empty name → reject; duplicate → reject;
- **Q4**: assumptions accepted — single warehouse; single actor (сотрудник отдела снабжения);
- **Q5**: whitespace-only name = empty → reject;
- **Q6**: distinct error message per violated rule;
- **Q7**: name-uniqueness lives in a shared Business Rules list, referenced by FRs;
- **Q8**: superseded — uppercase normalization was first accepted, then removed (see Q11);
- **Q9/Q10**: normalization extracted into a single defined term (D-1), not a «function»;
- **Q11**: comparison is **case-insensitive**; stored spelling = first entered (after trim).

Final accepted texts (canonical copy lives in `docs/requirements.md`):

- **D-1**: «Обработанное название — это введённое название без начальных и конечных пробелов».
- **BR-1**: «Обработанное название (D-1) товара содержит хотя бы один символ».
- **BR-2**: «Обработанное название (D-1) товара не совпадает (без учёта регистра) ни с одним названием товара из складского списка».
- **FR-1**: «Сотрудник отдела снабжения вводит название товара. Введённое название обрабатывается согласно D-1. Если нарушается BR-1 или BR-2 — операция отклоняется: складской список не изменяется, выводится сообщение об ошибке, соответствующее нарушенному правилу. Если BR-1 и BR-2 выполняются — в складской список добавляется товар: его обработанное название (D-1) и количество, равное 0».

Review notes (2026-09-07):

- Actor «сотрудник склада» corrected to «сотрудник отдела снабжения» (assignment text; confirmed by developer).
- Editorial: BR-1 recorded via the agreed simplified form + «товара» for self-sufficiency; D-1 word order normalized («без начальных и конечных пробелов»).

Conscious trade-offs are recorded as EL-1…EL-5 in `docs/requirements.md` (Section 7, «Accepted elaborations»).

## Global assumptions: ACCEPTED (2026-09-07)

A-1 and A-2 accepted as proposed (canonical texts in `docs/requirements.md`, Section 3);
FR-1 now references A-1. The term «складской список» is anchored in A-2: its meaning derives
from the single-warehouse assumption, so no separate D-2 is introduced.

## FR-2: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-3, FR-2, elaborations EL-6…EL-7.

Agreed decisions:

- **Q1**: search by processed name (D-1), case-insensitive, condition stated directly (no BR-2 inversion — BR-2 keeps the FR-1 polarity «нарушается → отказ»); BR-1 applies to every operation with name input (empty input rejected as BR-1, not as «не найден»); «удаляется товар» (domain language, not «строка»);
- **Q2**: product not found → rejection, list unchanged, own error message (EL-7);
- **Q3 → BR-3**: deletion allowed only at zero warehouse quantity; quantity belongs to the product, wording anchored to the deletion operation («на складе» kept — store quantities will appear in FR-7);
- «ненужный» = actor's judgment, not a system-checkable condition (note under FR-2);
- hard vs soft delete (historical data) deliberately deferred to the DB design phase.

## FR-3: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-1 (edition 2 — generalized),
BR-4, FR-3.

Agreed decisions:

- **Q1**: store input = name only; further attributes are not required by the методичка (future ideas, not promises);
- **Q2**: BR-1 generalized to all names (edition 2; D-1 was already entity-free); BR-2 kept product-specific, mirror rule **BR-4** introduced for stores — semantic shared, scope local, survives a third named entity;
- **Q3**: no counter analogue for stores — store↔product links arise from other operations; a store is added with its name only;
- two copy-paste slips caught at review («название товара» in the input branch; «BR-1 и BR-2» in the success branch) — mechanical, fixed during recording with developer's consent pattern; lesson recorded: template-slot checklist (entity, rule ids, list name) when cloning an FR.

## FR-4: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: FR-4, EL-8, OP-1 (new Section 9).

- **Q1 (draft by developer)**: first zero-slot-error draft (entity, rule ids, list, A-1, D-1, direct search, «не найден» — all correct); one mechanical gap (missing «список не изменяется + своя ошибка» in rejection branches) completed at recording;
- **Q2**: option (a) — FR-4 without a guard + **OP-1** (revisit store-deletion conditions when store requests are formalized after FR-7). A guard on an unformalized entity would be an unverifiable forward reference.

## Incident & repair (2026-09-07)

`docs/requirements.md` carried structural damage: BR-4 ordered before BR-3; canonical
FR-1/FR-2 texts displaced to the end of Section 6 and interleaved with EL-6/EL-7 table
rows. Present since commits `d7df353`/`f555fcc` — caused by the mentor's multi-part edits
and committed because only `git diff --stat` was reviewed, not the full diff (process
failure, acknowledged). The developer's uncommitted pastes (FR-1 variant without A-1,
draft FR-2 text) were detected during the check and superseded by the canonical restore.

Fix: sections 5–7 rebuilt to canonical accepted texts; EL-6…EL-8 in the table; Section 9
(Open points) added. Lesson recorded: review the **full** diff content before every commit.

Second occurrence, same day (commits `9ff8bf9`, `7cd613c`; repaired in `970da13`): EL-10/EL-11
rows landed outside the EL table (dangling after FR-5/FR-6 sections), a bullet marker lost in
Section 8. Root causes: (1) structural pre-commit check asserted row **presence**, not **order**;
(2) the diff was piped through `grep '^[+-]'`, stripping context so misplacement was invisible.
Strengthened check: order-aware scan (e.g. `awk` asserting EL-1…EL-n sequence inside Section 7)
plus an **unfiltered** `git diff` read before every commit.

Third occurrence (commit `ee4e6cc`, repaired in `f87a565`): the OP-1 closing-note edit reported
success but landed out of order (new «Status: closed» lines placed before the «Заведено…»
paragraph, old «Status: open» left in place). Two compounding factors: (1) the edit tool
applied the change at an unexpected position despite an exact-looking match — verify the
**file section itself** (`sed -n '/### OP-1/,/### OP-2/p'`) after touching narrative blocks;
(2) the pre-commit diff read was misleading at the terminal's wrap width — wrapped context
lines look like separate lines. Rule added: for every touched section, verify final file
content directly (sed/awk), not only the diff rendering.

## FR-5: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-5, FR-5, EL-9, OP-2;
EL-7 trace extended to FR-5.

Agreed decisions:

- **Q1**: input = product name + receipt quantity; term pair fixed: «количество поступления»
  (input) vs «количество товара на складе» (state);
- **Q2**: negative receipt rejected — it is a covert new operation (списание/отгрузка) absent
  from the seven assignment operations («мне кажется логичным» is not a requirement);
  domain observation: within the seven operations warehouse stock only grows, and combined
  with BR-3 a non-zero product can never be deleted → the developer's guard instinct was
  right but belongs to store requests/отпуск → **OP-2**; **BR-5** = positive integer;
  zero and fractional rejected (units = whole items, EL-9);
- **Q3**: «товар не найден» → rejection (single creation path via FR-1); UX suggestion
  «предложить выполнить FR-1» deferred to interface design (dropped from normative text);
- recurring draft gap (2nd time): failure-consequences clause («список не изменяется +
  своя ошибка») — template checklist now has **4** slots: entity, rule ids, list,
  failure consequences.

## FR-6: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: FR-6, EL-10; first future idea parked in Section 8.

Agreed decisions:

- **Q1**: displayed attributes = processed name + warehouse quantity (the only two artifacts define); receipt/creation timestamps rejected — not an artifact, «время поступления» is not a product attribute once receipts repeat (event history, deferred by design), parked as future idea;
- **Q2**: new **read-only template** correctly identified by the developer: no input (BR-1 n/a), no rejection branches, empty складской список = valid state with empty result, not an error;
- **Q3**: receipt-time ordering rejected (non-existent + ambiguous attribute, «интересно» is not a requirement); deterministic ordering chosen: alphabetical by processed name, case-insensitive (EL-10) — BR-2 uniqueness guarantees a total order with no ties.

## FR-7 planning decision (2026-09-07): DEFERRED — derived-operations phase opened

Developer's answers: Q1 — no accepted operation links товар↔магазин (correct);
Q2 — FR-7 cannot be completed without заявки and the product-store link (correct);
Q3 — option (а): formalize заявки/выдача first, then FR-7 (accepted).

Source grounding (методичка, Тема 4, extracted via `textutil`): the domain description
requires **four** data categories; two of them (per-store product name+quantity,
заявки на текущий год) are produced by **none** of the seven operations — the assignment
is internally incomplete. The «Разработать: модули ввода, изменения и просмотра данных»
clause grounds reconstructing the missing operations as **derived requirements**
(FR-8+, separate shelf: traced to the assignment, not among the seven named operations,
not extensions). FR-7 status → Deferred (blocked), stays reserved.

## Derived-set planning: AGREED (2026-09-07)

- Minimal set: **FR-8** (подать заявку) + **FR-9** (обработать заявку = отпуск
  склад→магазин); «обработка» и «перемещение» merged into one operation; direct transfer
  without заявка excluded (parked as future idea);
- **A-3** accepted («Система имеет доступ к текущей дате»); «текущий год» = год подачи
  заявки; no rollover/cleanup operation — old requests preserved, simply outside the
  «текущий год» definition;
- **EL-11**: заявка = single product (multi-line → extension candidate).

## FR-8: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-6, FR-8, EL-12…EL-14.

Agreed decisions:

- **Q1**: request fields = system-assigned unique number (invariant only — continuity
  explicitly not required, «+1 от 1» is an implementation detail for the DB phase;
  «ключ» avoided as DB terminology at requirements level) + submission date (A-3,
  system, not the actor) + store + product + requested quantity + **status**
  (missed by the developer in the draft, introduced at review: «подана» — the same
  creation-sets-initial-state pattern as FR-1's quantity 0);
- **Q2**: BR-6 = positive integer (developer's wording accepted verbatim); mirrors
  «магазин не найден»/«товар не найден»; no stock cap at submission — validation at the
  point of action (остаток проверяется при обработке);
- **Q3**: duplicates allowed, uniqueness on the request number only.

## FR-9: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-7, FR-9, EL-15…EL-18;
OP-2 closed (implemented by FR-9: BR-6 + BR-7). Both orphan data categories from
Section 2.1 now have producers: заявки (FR-8), per-store stock (FR-9).

Agreed decisions:

- **Q1**: re-processing a processed request → rejection «заявка уже обработана»;
  developer's proposed status «в работе» rejected — identical behavior to «подана»,
  and a rejection must not change entity state; lifecycle = «подана» → «обработана»;
- **Q2**: **BR-7** accepted (quantity ≤ stock, anchored to processing); partial
  fulfillment rejected for Phase 0 — needs an extra field + status; workaround exists
  (new request for the available quantity); parked as extension candidate; status
  «невозможно выполнить» rejected (impossibility = rejection, not a state);
- **Q3**: atomicity accepted («все три изменения — все или ничего», becomes a
  transaction at the DB phase); processing date recorded (A-3) — ML history;
- completed at recording: store-existence check symmetric to product check
  (store may be deleted via FR-4 between submission and processing) — motivates OP-1.

## OP-1 + FR-10: ACCEPTED (2026-09-07)

Accepted package recorded in `docs/requirements.md`: BR-8, FR-4 (updated to reference
BR-8), FR-10, EL-19…EL-20. Both open points are now closed (OP-1 here, OP-2 at FR-9).

Agreed decisions:

- **Q1 → BR-8**: developer's draft had correct holding-condition polarity; anchored to
  the deletion operation (BR-3 pattern) + grammar fixes («ни одной», «со статусом»);
- **Q2**: guard scope = only «подана» requests — guarding on all requests would kill
  the deletion operation (any store with history undeletable); processed requests
  referencing a deleted store are inert (FR-9 status precondition) and readable
  (the заявка carries the store name) — the hanging reference is not observable
  as breakage;
- **Q3 → FR-10**: accepted on the strongest possible argument — operational necessity
  (FR-9 input is a request number; without a view the system is unusable) + «модули
  просмотра» trace; mechanical completion by the FR-6 read-only template (fields as
  recorded by FR-8/FR-9, ordering by unique number, empty list valid); shows all
  years, year filter = future refinement (EL-20).

## FR-7: ACCEPTED (2026-09-07) — all 10 operations accepted

Accepted package recorded in `docs/requirements.md`: FR-7, EL-21.

- **Capstone assessment**: all substantive slots resolved correctly on the first draft
  (composition incl. every store; two-level alphabetical ordering with the right
  uniqueness arguments — BR-4 for stores, inheritance from BR-2 within a store;
  both empty cases with correct semantics: store-with-no-products displayed,
  empty store list = empty result, not an error);
- completed at recording (mechanical): «количество товара в магазине» terminology
  (FR-9 term), «без учёта регистра» for both orderings, explicit store-name group
  header, grammar, read-only примечание, zero-quantity impossibility note;
- growth reference: FR-1 took 11 question rounds; FR-7 — one round + mechanical edits.

## Phase 0 integrity check: PASSED (2026-09-07, one fix)

Mechanical consistency pass over `docs/requirements.md`:

- cross-references: every FR reference resolves to a declared artifact (no dangling ids);
  every BR/D/A is referenced — except **A-2** (found, fixed: anchor «складской список (A-2)»
  added at first Section 6 occurrence, FR-1);
- statuses: 10/10 FR Accepted; no Pending/Deferred; OP-1/OP-2 closed;
- quantity terminology uniform across inflections and line wraps (the four canonical
  terms; two «его количество» anaphora cases with in-sentence antecedents — acceptable);
- EL-1…EL-21 ordered; Section 2/2.1 tables consistent; typo scan clean.

## Phase 0 retrospective (2026-09-07)

Developer's answers + mentor commentary:

- **R1 (key decisions)**: developer — name identity (D-1 + case-insensitive uniqueness),
  deletion semantics (guards + history preservation), integer quantities. Mentor adds
  process picks: the A/D/BR/FR artifact separation (a rule lives once, FRs reference it),
  the derived-requirements shelf (Section 2.1, source-grounded gap analysis), and the OP
  mechanism (decisions deferred explicitly, never silently);
- **R2 (FR-1 again?)**: «кардинально ничего — последовательные вопросы и были обучением».
  Half-agreed: the process stays; what changed is the developer's toolkit — the 4-slot
  template checklist, holding-condition polarity, requirements/design/UX level
  separation. Evidence: FR-1 took 11 question rounds, FR-7 one pass;
- **R3 (artifact value)**: most useful — developer: FR; mentor: BR/D/A (reference counts:
  D-1 ×14, A-1 ×10, BR-1 ×9 — the smallest artifacts had the highest reuse; BR-2 alone
  provided FR-6's total order). Most expensive — developer: EL (agreed: 21 rows of
  append-only narrative needing trace discipline; the point: it is the audit trail of
  every decision beyond the методичка — interview capital); empirical runner-up:
  the FR section (all three structure incidents landed there).

## Next step

**Phase 1 — Design** kickoff:

1. `docs/architecture.md` — modular monolith outline (API / Service / Repository /
   PostgreSQL), vertical-slice plan mapped to FR-1…FR-10;
2. `docs/database.md` + first schema sketch (Alembic comes with code): entities and
   attributes already named by requirements (товар: название, количество на складе;
   магазин: название; заявка: номер, статус, даты, магазин, товар, количество;
   количество товара в магазине). Open design decisions: hard vs soft delete
   (history/ML), case-insensitive unique indexes, request-number generation;
3. first vertical slice candidate: product (FR-1/FR-2/FR-5/FR-6) end-to-end.

## Architecture doc + ADRs: DONE (2026-09-07)

`docs/architecture.md` (draft v1) + `docs/decisions/ADR-0001…0004` created.

Design Q&A (mentor questions → developer answers → decisions):

- **Q1 transaction owner**: developer — Service («business logic, not a single SQL
  query»); accepted, reasoning completed: a transaction is a property of a use case,
  FR-9 spans three aggregates, no single repository owns them → **ADR-0003**;
- **Q2 BR-2 guard**: developer proposed all three layers; refined to **service +
  DB unique index** (ADR-0004): the repository pre-SELECT is racy duplication; the
  index is the only guarantee; the repository translates `UniqueViolation` into the
  same domain error — two sources, one outcome;
- **Q3 packaging**: developer chose **layer-first** for readability at this scale —
  accepted (ADR-0002) with an explicit revisit trigger (>8–10 files per layer folder
  / second developer).

## Database design: DONE (2026-09-07) — spawned OP-3

`docs/database.md` (schema v1) + `ADR-0005` created. Design Q&A:

- **Q1 keys**: surrogate ids everywhere (developer) + unique business `number`
  for заявка (sequence; Postgres allows one identity column per table — hence an
  explicit `store_request_number_seq`);
- **Q2 store_product**: (store_id, product_id) composite PK + quantity;
  `CHECK (quantity > 0)` per FR-7 (zero row cannot exist; developer's «0 логичнее»
  instinct parked in future ideas); PK leading column serves FR-7 grouping;
- **Q3 references**: option (в) — plain FK (RESTRICT) + soft delete, no snapshots;
- **Q4 deletion**: soft delete for product and store (ADR-0005); partial unique
  indexes over live rows; the two soft-delete taxes documented;
- notable invariants: cross-column CHECK on store_request
  (status ⇔ processed_at), BR-8-serving partial index on pending requests.

**Design-review discovery → OP-3** (requirements gap): BR-3 ignores per-store
quantities — a product can be soft-deleted while stores still hold it. FR-7
semantics for such rows depend on the resolution.

## OP-3: CLOSED (2026-09-09) — delisting semantics

Developer's resolution: option (ii), BR-3 unchanged — with a semantics definition, not
just a pick: складское удаление = assortment delisting («больше не заказываем»);
store остатки = physical reality drained by the stores' own process (outside scope, A-1).
The BR-3/BR-8 «asymmetry» is thereby explained, not patched: BR-8 watches our activity
(заявки), BR-3 watches our stock; store stock is not ours to guard. FR-7 showing
delisted-but-present products = intended truth. Recorded: EL-22, FR-7 примечание,
future idea (inter-store transfers). Review note: the developer named the price of the
choice aloud and parked the scope-creep temptation — Phase 0 discipline holding.

## Slice 1 (products): DONE (2026-09-09) — a80bba5

First vertical slice end-to-end, 29/29 tests green (unit 12, integration 5, API 12)
against real PostgreSQL 16 (Docker). Live smoke test: trim by D-1, qty 0 (EL-2),
case-insensitive duplicate → 409 with BR-2 message.

- scaffold: pyproject (pythonpath for pytest), docker-compose (postgres:16 + healthcheck),
  README quick start; venv on Python 3.14.3 (fixed: stale .venv from an earlier attempt
  mixed 3.9/3.14 — recreated);
- app/: domain-first (ADR-0002 ред. 2) — `app/products/` (models, schemas, repository,
  service, router) + `app/shared/` (config via pydantic-settings, db session, typed
  domain errors); `app/main.py` app factory + DomainError→HTTP mapping (EL-3);
- migration 0001: product table + partial unique index `product_live_name_key` +
  CHECK warehouse_quantity >= 0 — verified live via `\d product`;
- service layer: FR-1/FR-2/FR-5/FR-6 with BR-1/BR-2/BR-3/BR-5, soft delete (ADR-0005),
  ADR-0004 in action (flush IntegrityError → DuplicateProductNameError; covered by a
  unit test with a fake session);
- fixes during bring-up: alembic env.py needed sys.path shim for `app.*`; stray `Func`
  import in models.

## Slice 2 (stores): DONE (2026-09-10)

Developer-written slice (first own code) under mentor review; finalized jointly.
48/48 tests green (19 new: unit 9, integration 4, API 6) against real PostgreSQL.
Live smoke: trim by D-1, case-insensitive duplicate → 409 with BR-4 message, GET list.

- Q0 decision → **FR-11** (derived, GET /stores) recorded in requirements.md —
  FR-10-style trace (operational necessity + «модули просмотра»);
- BR-8 marked in code as a grep-able comment (`# BR-8 (FR-4): guard pending…`)
  — vacuously true until slice 3;
- review findings fixed (developer's draft): store error classes were nested inside
  another error class (indentation → module-level ImportError); migration 0002 had
  `revision="0001"/down_revision=None` (two heads); stores_router was not mounted in
  main.py (masking the ImportError); conftest TRUNCATE extended to store; cosmetics
  (unused imports, docstring copy-paste, dead commented constraint).
  Lesson recorded: grep "line exists" ≠ "behavior works" — verification is by import/run;
- ops note: after a host reboot Docker Desktop must be started manually (`open -a Docker`);
  without the running daemon the compose plugin is unavailable and all DB tests fail
  with connection errors — check `docker info` first when integration tests suddenly error.

## Slices 3+4 (requests, FR-7 view): DONE (2026-09-15) — all 11 FR implemented

Slice 3 (requests, `3565aae` + `084eaab`): 82 tests. Slice 4 (FR-7, this commit): +7 → **89 tests**.

Slice 4 summary: developer built the core (query with LEFT JOINs + setdefault grouping —
reviewed clean after fixes: dead `find_id_by_name` removed, honest annotations,
`list(grouped.items())` return); mentor completed schemas/router/tests. Route:
`GET /stores/stock` → nested JSON per EL-21/EL-22. Key test: delisted-but-present
product is shown (EL-22); empty store displayed with `products: []`.

Mentor's own test bugs caught by the run (kept as a lesson): wrong Russian-alphabet
expectation (С < Я), helper param name mismatch — code was right, tests were wrong.

All 11 FR (FR-1…FR-11) are now implemented end-to-end: 4 migrations, 89 tests
(unit 24 / integration 17 / api 24? — see pytest), PostgreSQL via Docker.

## Slices retrospective (2026-09-15)

- **R1 (что могу сам)**: всё, кроме тестов — honest. Phase 2 plan: first slice is
  **test-first** (developer writes tests before implementation; mentor reviews tests
  as code). Testing is also the core ML-engineer skill (boundaries, invariants,
  leakage checks);
- **R2 (hardest slice)**: requests — cognitive load of three aggregates + one
  transaction + status machine + cross-domain composition; survived by small
  review packages, each verified before submission;
- **R3 (slice 2 redo)**: «последовательно писать и сразу проверять» — the discipline
  actually demonstrated by slice 4 (the delta between slices 2 and 4 is measurable:
  first-review defect count dropped to near zero).

## PHASE 1: COMPLETE (2026-09-15)

Design (architecture.md, database.md, ADR-0001…0005) + implementation: 11/11 FR
end-to-end, 4 migrations, 89 tests, live demo script (`scripts/demo.sh`), all
artifacts traceable to requirements (FR/BR/EL ids in code and messages).

## CLI menu slice: DONE (2026-09-24) — original assignment fully delivered

`app/cli.py` — the third door to the same services (after unit tests and API):
11 operations + exit, dictionary-dispatch MENU, one DomainError catch in the loop
(Q1), `_STATUS_RU` imported not duplicated (Q2/DRY), `ask_int` for mechanical
parsing (Q3). Refactored for testability: `run_menu(ui, services)` extracted from
`main()` — "untestable code asks to be changed".

Developer path this slice: skeleton review (placeholders shuffled, menu gaps,
missing ui) → all 11 handlers (7 clean, live smoke caught `.items()` on a list
contract + str-vs-Enum `.value`) → own CLI tests (3/5 tested the wrong thing —
fixed with named-by-behavior rewrites + FailingProducts fake; a lesson in
"assert what you meant, not what you wrote"). Result: **98/98 tests**.

Assignment trace complete: «Разработать: меню системы; модули ввода, изменения
и просмотра данных» — menu ✓, modules ✓ (11/11 FR via three doors: tests/API/CLI).

## ML track: baselines + LightGBM (2026-10-06) — baseline beaten

Полный цикл: разведка (docs/img/: тренд +35%, годичная сезонность ×1.89,
стабильный недельный профиль, шум дня 0.27) → гипотезы H1–H4 → 8 фичей
(leak-safe by construction: поштучный build_features + векторизованная
обучающая таблица, скреплённые тестом согласованности) → walk-forward →
MLflow-трекинг всех прогонов.

Результаты (kaggle, 50 пар, 2013–2017):

| модель | MAE | WAPE |
|---|---|---|
| naive | 9.72 | 20.5% |
| seasonal_naive_7 | 7.90 | 16.7% |
| moving_average_7 (планка) | 7.67 | 16.2% |
| **lightgbm (retrain/28d)** | **5.79** | **12.2%** |
| **lightgbm, full 500 pairs** | **6.01** | **11.5%** |

Победа устойчива на полном датасете (−21.6% MAE); важности на 500 парах:
month 23.6%, pair-level 22.3%, rolling 18.4%, dayofweek 11.5% — все четыре
гипотезы подтверждены дважды (50 и 500 пар); year избыточен при наличии
days_from_start.

Инженерные находки: warmup=8 (shift(7) опустошает 7-дневную историю — поймано
живым прогоном); переобучение кэшируется (retrain_every), прогноз — поштучным
leak-safe путём; важности и разбор ошибок встроены в evaluate-скрипт.

## ML retrospective (2026-10-08)

- **R1** (самое неожиданное): «метрики меняются в зависимости от данных» — the
  baseline table flipped on real data (seasonal_naive dethroned). Built-in
  consequences: data-version params in every MLflow run; exploration before
  hypotheses;
- **R2** (leakage, why shift(1) before rolling): honest gap — answered vaguely,
  mentor explanation recorded: rolling at day D covers D−6…D (includes the
  target!); shift(1) first → window D−7…D−1. The consistency test works because
  the per-day build_features is an ORACLE — leak-proof by construction — so any
  vectorized leak breaks row equality. TOPIC TO REVISIT before Phase 3 ML work;
- **R3** (next improvement, WAPE < 10%): developer — hyperparameters, news/shock
  data, holidays. Mentor priority: holidays/calendar first (cheap, grounded in
  our own charts: December dip, July peak), params second (small gains), news
  data — an honest far shelf (sourcing + alignment + overfit risk).

## PHASE 2: COMPLETE (2026-10-08) — v0.2.0

Event history + CI + Docker + seed + dataset contracts + baselines + MLflow +
Kaggle stage + LightGBM (full 500 pairs: MAE 6.01 / WAPE 11.5%, baseline beaten
by 21.6%). 126 tests green.

## Forecast slice: DONE (2026-10-09, `5ae9708`)

`GET /forecast?store_id&product_id&days (1–14, default 3)` + `POST /forecast/retrain`
(manual, форс-мажор per Q1). Design decisions (Q&A 2026-10-08): TTL-cached model
(72 h) + manual retrain; history < 30 days → baseline moving-average with honest
`model`/`warning` fields (Q2: baseline is a legitimate model for small data);
recursive horizon (day D+2 uses D+1 prediction as lag input). Service takes an
injected history loader → unit tests run on synthetic frames.

Tests: 133/133 (unit 7 + api 2 new). Live demo OK (weekday profile visible in
3-day forecast). Known small issue: forecast dates carry the time-of-day of the
the last event — normalize to midnight (CLOSED 2026-10-09, see the next section).

## Day-boundary fix: DONE (2026-10-09)

Known issue закрыт — и оказался глубже косметики: `load_from_stock_event`
нарушал контракт датасета (сырые метки со временем, без агрегации по дням,
без сетки с нулями). Kaggle-адаптер удовлетворял контракту «бесплатно»,
а тесты кормили сервис чистой синтетикой — сломан был только прод-путь
(«тесты проверяли не тот контракт»). Полная цепочка разбора с разработчиком:
симптом → факты (seed пишет 8–20 UTC; адаптер только переименовывал колонки) →
дизайн-Q&A:

- **Q1**: контракт чинит АДАПТЕР, где он объявлен (docstring обещает
  «взаимозаменяемость» — починка в потребителе превратила бы контракт
  в convention; входов у сервиса два — forecast/retrain);
- **Q2**: переиспользован `build_demand_dataset` — «события → дневной спрос»
  одно знание, одна реализация (там уже живёт пойманный tz-шрам);
  адаптер: конвертация зоны + фильтры по локальному дню + empty-case
  с честными dtype (путь пустой БД в API-тестах);
- **Q3**: граница дня = бизнес-таймзона → **ADR-0007**
  (`Settings.business_timezone`, default Europe/Moscow). Порядок операций
  проверен живым прогоном: `tz_convert → tz_localize(None) → normalize`
  (сброс зоны первым принял бы UTC за локальное); `tz_localize(None)` на
  наивных — no-op, датасетный слой совместим без правок.

Валидация: +4 регресс-теста на адаптер («грязные» метки: время внутри дня,
дубль дня, пропуск дня, пересечение границы 21:10 UTC = 00:10 след. дня
Москвы; пустая БД) — **137/137**. Live smoke на сид-данных: полная сетка
56 дн. × 12 пар = 672 строки, даты прогноза — наивные полуночи.

## CLI пункт 12 «Прогноз спроса»: DONE (2026-10-12)

Mentor Mode, developer-first: wiring, handler, сервисные методы и тесты написаны
разработчиком под поэтапным ревью (4 раунда). Финальная сборка доведена совместно
(вывод model/warning, константы в роутере, D-1/BR-1 в резолве имён, тесты).

- резолв имён → id: тонкие read-методы `get_live_id_by_name` на StoreService/
  ProductService (D-1 strip + BR-1 внутри, как у остальных операций) — CLI
  ходит только в сервисы; NotFound ловит существующий DomainError-catch меню;
- `ForecastService` собран в `build_services` с per-call загрузчиком (своя
  сессия на вызов — паттерн API-роутера, симметрия дверей);
- горизонт 1–14 стал инвариантом СЕРВИСА: `MIN/MAX_FORECAST_DAYS` +
  параметризованный `InvalidForecastHorizonError` (errors.py — лист
  dependency-дерева, без импортов); роутер импортирует константы;
- вывод: даты-полночи, метка модели, warning baseline, склонение дней.

Живые уроки ревью: вызов FastAPI-провайдера из CLI; методы в репозитории вместо
сервиса; приватный метод снаружи класса; чужая сигнатура конструктора;
`except Exception`; цикл по верхнему dict вместо result["forecast"]; импорт
констант в errors.py → ImportError (цикл зависимостей); двойник, врущий о
контракте; тест без «12» в стенограмме диалога → StopIteration в ЧУЖОМ handler'е
(диалог FakeUI начинается с выбора пункта меню).

Тесты: +2 на handler (резолв+вывод; LookupError — сообщение и выживание меню),
тест меню 12→13 пунктов → **139/139**. Live smoke: прогноз на 3 дня,
lightgbm, даты-полночи.

## Holiday features: DONE (2026-10-12) — небольшой, но устойчивый выигрыш

Срез по полному циклу: гипотеза H5 разработчика («до праздника рост, после
спад») → разведка с снятием конфаундов → фичи → A/B walk-forward.

- **Разведка** (`scripts/explore_holidays.py`, `docs/img/holidays_profile.png`):
  нормировка «день / те же дни недели ×4 нед.» убирает ДВА конфаунда —
  недельный профиль и летне-зимний тренд; H5 ОТКЛОНЕНА (предпраздничного
  роста нет), единственный устойчивый сигнал — «полоса закрытия»
  Рождества/НГ (0.83–0.91 на −5…+3), пересекающая границу месяца →
  дистанция несёт инфо сверх `month`;
- **Фичи**: `days_to/from_holiday` + `HOLIDAY_FAR = 999` (знание «далеко»,
  не NaN: константа режется порогом, NaN — спецмеханизм и не режется
  в sklearn-деревьях); ЕДИНСТВЕННАЯ реализация расчёта `_holiday_distances`
  в обоих путях — согласованность по построению; календарь — инъекция
  (`frozenset[date]`), как history_loader; генерация с запасом лет (+2),
  иначе фича молча выродится в 999;
- **A/B** (walk-forward, retrain/28d, MLflow): 50 пар 5.79→5.77;
  **500 пар: MAE 6.01→5.96 (−0.8%), WAPE 11.5→11.4%**. Обе ветки контроля
  воспроизвели Phase 2 в точности (константные фичи 999 ничего не меняют —
  проверено). Честная интерпретация: `month` + `days_from_start` уже несут
  большую часть декабрьской ямы, маржинальная информация дистанции мала;
  направление эффекта одинаково на обоих объёмах — оставляем;
- **ForecastService**: календарь СОЗНАТЕЛЬНО пуст (RU-сид без праздничного
  сигнала; фича вырождена в 999, вреда нет) — решение зафиксировано
  в docstring с инструкцией на будущее (RU-календарь при реальных данных);
- **Leakage-ретроспектива R2 закрыта** (2026-10-12): разобраны shift(1)
  перед rolling, границы по построению, random split как маскировка утечки
  (автокорреляция соседей + подтверждение утекшей фичи в тесте) vs
  walk-forward как симуляция деплоя.

Уроки среза: конфаунды в разведке (два!), «фича из данных vs из календаря»
(первая реализация тянула дистанции из history — KeyError/утечка .last());
ментор дважды ошибся в собственных тестах (перепутаны 6/9, чужой календарь
в ассерте) — «код прав, тесты врут» повторился в обе стороны.

## Multi-day horizon evaluation: DONE (2026-10-13) — обещание 1–14 дней доказано

Протокол: БЛОЧНАЯ (эпизодическая) оценка — в якорный день T знание замораживается
(история строго < T), рекурсивный прогноз уходит на 14 дней (прогнозы кормят
лаги), каждый k сверяется с фактом. Реализовано: `recursive_forecast` +
`blocked_horizon_evaluate` в `baseline.py` (DataFrame-контракт, все пары;
тот же протокол честно применён и к бейзлайнам), 4 юнит-теста (заморозка
naive, недельный цикл seasonal_naive — k=8 читает прогноз k=1; регрессия
iloc[0] — все пары; граница заморозки мутацией будущего),
`scripts/evaluate_horizon.py` + график `docs/img/horizon_degradation.png`.

Гипотезы H6a/b/c зарегистрированы ДО прогона — **все три опровергнуты**:

- **H6a ❌**: модель ПЛОСКАЯ по k (500 пар: 5.50–6.86 MAE, излома на k=8
  нет). Контроль «тот же день недели» (шаг 7 кладёт якоря на один weekday →
  пары k и k+7 сравнимы без недельного конфаунда): неделя рекурсии стоит
  ~0.03–0.05 MAE. Механизм: модель опирается на календарь и уровень пары
  (важности: month 23.6%, pair 22.3%) — они не «гниют»; рекурсия сходится
  к сезонному среднему, а не к мусору;
- **H6b ❌**: seasonal_naive деградирует (9.5→10.0; пилот: излом 8.53→8.95
  на k=8) — замороженная неделя отдаляется от факта второй недели;
  moving_average к k=8–9 целиком из прогнозов (пилот: пик 9.67);
- **H6c ❌ (знак наоборот)**: gap модель-бейзлайн РАСТЁТ с k — WAPE по всему
  горизонту 10.5% vs 15.4% (snaive) / 15.8% (ma7); на k=14 отрыв ~32%.

Методологическая находка: шаг 7 = все якоря на одном weekday → профиль
по k конфаундится с днём недели (видно по качелям ma7), но пары (k, k+7)
дают чистую меру деградации рекурсии. Пилот 50 пар/шаг 2 и финал 500 пар/
шаг 7 согласованы; всё в MLflow (protocol: blocked_horizon).

Живые уроки среза: ревью разработки — два красных бага в рекурсии
(iloc[0]: обслуживалась только первая пара из 50 — тихая порча цифр;
actual без date → KeyError на первом якоре); «зарегистрированная гипотеза
опровергнута» — лучший исход эксперимента: интуиция «лаги прогниют» была
убедительна и неверна.

## Replenishment recommendations: DONE (2026-10-13) — прогноз превращён в решение

EX-2 зафиксирован в requirements §8.1 (заодно догнан EX-1 — прогноз как
extension не был записан). Срез: политика order-up-to
(Q = ceil(F + z·σ·√(L+H) − stock)) вынесена в ЧИСТЫЙ модуль
`app/recommendations/policy.py` — ТА ЖЕ формула работает в сервисе и в
бэктесте (одна реализация, как с праздничными дистанциями); сервис
агрегирует прогнозы по парам (продаж в магазинах нет — рекомендовать можно
только складу), σ = std дневного агрегированного спроса за 28 дня (Q4;
вариант «σ из остатков прогноза» — future idea). Три двери: API
`GET /recommendations` (4 новые DomainError → 422; перекрёстное правило
L+H≤14 живёт в сервисе — в Query его не выразить), CLI пункт 13 (параметры
с дефолтами: пустой ввод = 0.95/3/7), тесты (+31 unit, +7 api, +3 cli).

Бэктест (`scripts/evaluate_replenishment.py`, MLflow protocol:
replenishment_backtest): симуляция периодического обзора — якоря каждые
H=7 дн., поставка L=3, знание заморожено до якоря, сток виртуальный,
необслуженный спрос фиксируется. Полный объём (500 пар, 52 якоря):

```text
policy             fill_rate  avg_stock  stockout_days
naive                0.9901      1820        5.5%
order_up_to_95       1.0000      2204        0.04%   (×1.21 запаса)
order_up_to_99       1.0000      2383        0.00%   (×1.31 запаса)
```

Гипотезы H7a/H7c подтверждены, **H7b опровергнута** — и это главная
находка среза: интуиция «без страхового запаса — стокаут в половине дней»
врёт для катящейся order-up-to системы. Механизм: цель W=L+H против цикла
обзора H даёт структурный буфер (каждое прибытие садится с ≈H днями
покрытия), а fill rate считает единицы спроса, а не вероятности — стокауты
naive редки и мелки (−18% спроса плохого дня). Маржинальность честная:
SS добавляет последние ~1pp fill rate за +21% запаса; 0.99 против 0.95 —
ещё +8% запаса почти впустую (нелинейность z: 1.645→2.326). Реализованный
fill rate 1.0 при номинальном SL 0.95 ожидаем: fill rate ≠ cycle service
level (оговорено в docstring) + цель W=10 перекрывает экспозицию цикла 7.

Живые уроки среза: float-шум в ceil (0.1+0.2−0.3 = 5.5e-17 → Q=1) —
гвардия round(need, 6) + тест на точной границе; match-паттерны
pytest.raises чувствительны к регистру («Время поставки» vs «время
поставки» — два красных прогона из-за заглавной буквы).

## Phase 4 — Web UI (EX-3): шаги 0–13 DONE (2026-10-21)

Обсуждение закрыто 2026-10-19 (6 стадий): React+TS+Vite, палитра №4745 (тёмный
сайдбар + светлый контент), read-write тонкий клиент (**ADR-0008**), single origin:
FastAPI раздаёт собранный бандл, в dev — Vite proxy (**ADR-0009**), Chart.js,
re-fetch после мутаций, полный UI всех 11 операций (требование преподавателя).

- **0–3**: EX-3 в requirements §8 + ADR-0008/0009; `feat!:` REST под `/api`
  (196→192 теста — часть контрактов была route-level); `GET /api/forecast/history`
  (хвост факта для графика); `/img` + SPA-fallback (`SPAStaticFiles`; урок:
  `StaticFiles` бросает starlette-`HTTPException` — fastapi-подкласс его НЕ
  ловит, ловить надо родителя);
- **4–10**: скаффолд frontend/ (сайдбар, api-клиент, shared-компоненты) + 6
  страниц: склад (FR-1/2/5/6), магазины + FR-7 секцией (FR-3/4/7/11), заявки
  (FR-8/9/10), прогноз (факт+прогноз Chart.js, пунктир baseline, retrain),
  рекомендации (параметры политики, бейджи статусов), аналитика (пайплайн,
  таблицы метрик, методологические графики из /img). 18 vitest-тестов;
- **11**: multi-stage Docker — node:22-slim собирает SPA, python:3.13-slim
  раздаёт (Node в runtime-образе нет); `libgomp1` для LightGBM (slim без
  OpenMP); lightgbm+scikit-learn перенесены в runtime-депы — ForecastService
  импортирует LGBMRegressor на уровне модуля (худой образ вскрыл пробел:
  в dev scikit-learn приезжал транзитивно через mlflow); контекст сборки
  почищен (mlartifacts 179 МБ в .dockerignore; ui-скриншоты — README-актив,
  в образ не попадают). Smoke живым прогоном: SPA, fallback на /forecast,
  JSON-404 в /api, /img, POST/DELETE сквозь контейнер, lgbm import — все
  зелёные; 196 pytest;
- **12**: CI job `frontend` (npm ci → tsc+vite build → vitest), параллелен
  backend-job; CI зелёный;
- **13**: README — галерея скриншотов `docs/img/ui-*.png`, dev-режим фронтенда
  (порт 5173, proxy /api), полный стек одной командой.

### UI polish and documentation follow-up (2026-10-22)

After steps 0–13, the following follow-up commits polished the UI and aligned
the README screenshots with the current layout:

- [`ce8b692`](https://github.com/zlatopol/inventory-intelligence/commit/ce8b69274b8f34b76ac5598829416229f0ef3ac5): adjusted sidebar spacing.
- [`d497b85`](https://github.com/zlatopol/inventory-intelligence/commit/d497b8534ffc80e6b8d99d33b668a1577de0234c): added progressive list pagination, prioritized pending requests, and placed forms before tables.
- [`cebfadc`](https://github.com/zlatopol/inventory-intelligence/commit/cebfadc06babbac81ba3bfc19e223af55ca64704): refreshed UI screenshots for the forms-first layout and list pagination.
- [`4707ba3`](https://github.com/zlatopol/inventory-intelligence/commit/4707ba3dd7a6ee3d1040f171a6b030902de36dcc): updated the UI screenshots again.

Developer-reported validation: tests pass locally and the checks triggered when
changes are pushed to Git are successful. Tests were not rerun while preparing
this status update.

### Phase 4 retrospective

#### What went well

1. **Iterative UI refinement.** After the core flows were implemented, layout and
   list behavior could be improved in focused follow-up changes.
2. **Work-oriented request ordering.** Pending requests appear first, making
   records requiring action easier to find.
3. **Progressive list display.** The “Show more” pattern reduces the initial
   visual load on long lists while keeping additional records accessible.
4. **Documentation alignment.** Screenshots were refreshed to reflect the
   current interface rather than an earlier layout.
5. **Validation workflow.** Local tests and Git-triggered checks provide
   repeatable feedback when changes are introduced.

#### What to improve

1. **Keep implementation and documentation synchronized.** Update the status
   log and screenshots as part of the same task as substantial UI changes.
2. **Standardize list behavior.** Reuse consistent conventions for sorting,
   initial visible counts, and progressive expansion across pages.
3. **Check shared styles across screens.** CSS changes can affect pages beyond
   the one being actively edited; regression checks should cover shared layouts.
4. **Use a completion checklist.** Before closing a phase, verify functionality,
   tests, CI, screenshots, and project documentation together.

#### Conclusion

Phase 4 is complete. The October 22 follow-up commits are UI polish and
documentation alignment, not a new development phase. The frontend now has the
six documented screens, the agreed operations, analytical views, and refreshed
screenshots.

The next functional increment is manual sales registration with transactional
store-stock deduction and a sale event in stock history. Treat it as a separate
feature covering database migration, business logic, API, frontend, and tests.

Suggested acceptance criteria for sales registration:

- Store stock never becomes negative.
- Sale creation and stock deduction are atomic.
- Each accepted sale is recorded in stock-event history.
- Retries cannot cause duplicate deductions.
- Failures do not leave a partially applied sale.
- API and UI behavior are covered by tests.
- Documentation reflects the implemented behavior.

## Next step

1. Implement manual sales registration and atomic store-stock deduction.
2. Record the sales event in stock history and expose it through the API/UI.
3. Keep parked ML follow-ups separate: hyperparameters (R3), scheduled
   retraining, MLflow server, and forecast monitoring.

## Repository notes

- 2026-09-07: FR-1 package committed (`docs: record accepted FR-1 package`); `docs/requirements.md` filled with accepted artifacts and grows as FR-2…FR-7 are accepted.
- Earlier note about untracked `.github/`/`docs/` is obsolete: everything had already been committed in `8bae47d`; working tree was clean before this change.
