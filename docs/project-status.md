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

## Next step

1. Agree global assumptions **A-1** (single actor — сотрудник отдела снабжения) and **A-2** (single warehouse; складской список) and the recording principle: FR texts reference assumptions by id (FR-1 becomes «Сотрудник отдела снабжения (A-1) вводит…»). Proposed A-1/A-2 texts submitted to the developer on 2026-09-07.
2. → **FR-2** «удалить ненужный товар из складского списка» — Mentor Mode, mentor opens with clarifying questions.

## Repository notes

- 2026-09-07: FR-1 package committed (`docs: record accepted FR-1 package`); `docs/requirements.md` filled with accepted artifacts and grows as FR-2…FR-7 are accepted.
- Earlier note about untracked `.github/`/`docs/` is obsolete: everything had already been committed in `8bae47d`; working tree was clean before this change.
