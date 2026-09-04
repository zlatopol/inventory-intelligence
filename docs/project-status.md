# Project Status

Last updated: 2026-09-04

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

## FR-1 status: final iteration

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

Accepted artifacts:

- **D-1** (definition; final name pending, suggestion: «Обработанное название»):
  «Обработанное название — это введённое название без начальных и конечных пробелов».
- **BR-1** (accepted):
  «После удаления начальных и конечных пробелов название товара содержит хотя бы один символ»
  (optional simplification: «Обработанное название (D-1) содержит хотя бы один символ»).

Pending:

- **BR-2** — **not yet accepted**. Current developer wording («Название товара совпадает с названием товаров из списка склада») has inverted polarity (describes the violation condition). Final form must be a holding condition, pattern:
  «Обработанное название товара не совпадает (без учёта регистра) ни с одним названием товара из складского списка».

Conscious trade-offs (mark as «Принятое уточнение» in requirements.md):

- stored spelling = first entered (cosmetic inconsistency across products is possible);
- all reject/error behavior is an elaboration of the assignment (the методичка does not describe error scenarios).

## Next step

1. Developer submits the final FR-1 package: D-1 (final name), BR-2 (correct polarity, case-insensitivity stated in the rule text), FR-1 referencing BR-1, BR-2, D-1.
2. On acceptance → fix recording principle (actor + single warehouse live in global assumptions referenced by all FRs) → **FR-2** «удалить ненужный товар из складского списка».

## Repository notes

- Git: `main` @ `cd5d324`; `.github/` and `docs/` are still untracked (to be committed).
- `docs/requirements.md` exists but is empty — to be filled from agreed FRs as FR-1…FR-7 are accepted.
