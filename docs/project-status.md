# Project Status

Last updated: 2026-09-07

## Current phase

**Phase 1 — Design** (opening).

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

## Next step (updated)

**`docs/database.md`** — schema design discussion (Mentor Mode), questions to open:

- Q1: surrogate PK (id) vs natural key (name) — and what `lower(name)` unique index
  means for both;
- Q2: where per-store product quantities live (junction table store_product?), and
  why FR-7's read pattern matters for its shape;
- Q3: заявка table — number generation (sequence vs max+1 under ADR «uniqueness only»),
  status domain, store/product references after deletion (inert history, EL-19);
- Q4: hard vs soft delete for products/stores (BR-3/BR-8 guards + ML history interest);
- Q5: integrity last line — CHECK (quantity >= 0), FK behavior, timestamps.

## Repository notes

- 2026-09-07: FR-1 package committed (`docs: record accepted FR-1 package`); `docs/requirements.md` filled with accepted artifacts and grows as FR-2…FR-7 are accepted.
- Earlier note about untracked `.github/`/`docs/` is obsolete: everything had already been committed in `8bae47d`; working tree was clean before this change.
