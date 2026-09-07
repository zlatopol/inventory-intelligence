# Project Status

Last updated: 2026-09-07

## Current phase

**Phase 0 — Requirements formalization** (in progress).

Scope of Phase 0: only **Original Assignment Requirements**. No PostgreSQL, SQLAlchemy, FastAPI, Docker, ML, DB tables, architecture, or API design at this stage.

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

## Next step

**FR-8** «подать заявку магазина» — Mentor Mode, questions submitted 2026-09-07:

- Q1: заявка structure — fields incl. system-assigned number (first entity in the project
  without a natural unique key — stores/products are keyed by name, requests are not)
  and submission date (A-3);
- Q2: validation set — BR-1 for both names, «магазин не найден» / «товар не найден»
  mirrors, quantity rule (BR-6 candidate: positive integer); open sub-question: should
  the requested quantity be capped by the current warehouse stock at submission time?
- Q3: duplicates — two identical requests (same store+product) allowed? Expected:
  yes (uniqueness lives on the request number only).

## Repository notes

- 2026-09-07: FR-1 package committed (`docs: record accepted FR-1 package`); `docs/requirements.md` filled with accepted artifacts and grows as FR-2…FR-7 are accepted.
- Earlier note about untracked `.github/`/`docs/` is obsolete: everything had already been committed in `8bae47d`; working tree was clean before this change.
