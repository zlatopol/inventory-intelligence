# Requirements

> Phase 0 — requirements formalization (in progress).
> Artifacts are recorded here as they are accepted. Normative texts (A, D, BR, FR) are kept
> in Russian — the language of the source assignment. Document scaffolding is in English.

## 1. Source and discipline

Primary source: `docs/source/ТРПО_КР.doc` — методические указания СПбГЭТУ «Технология
программирования» (В.Л. Литвинов), Тема 4 «Информационная система СНАБЖЕНИЕ отдела
снабжения оптовой базы».

Separation rules:

- **Original assignment requirements** — only what traces to the методичка (Sections 2–7).
- **Project extensions** — features added for portfolio purposes (Section 8).
- **Future ideas** — optional, not committed to (Section 8).

## 2. Original operations

The assignment defines seven operations; agreed FR order:

| FR | Operation (original wording) | Status |
|----|------------------------------|--------|
| FR-1 | «включить новый товар в список товаров на складе» | **Accepted** |
| FR-2 | «удалить ненужный товар из складского списка» | Pending |
| FR-3 | «включить новый магазин в список магазинов» | Pending |
| FR-4 | «удалить ненужный магазин из списка» | Pending |
| FR-5 | «учесть поступление некоторого товара на склад» | Pending |
| FR-6 | «просмотреть информацию о товарах на складе» | Pending |
| FR-7 | «просмотреть информацию о товарах по магазинам» | Pending |

Note: store requests («заявки магазинов на текущий год») appear in the assignment's domain
description but are not among the seven operations — to be discussed separately after FR-7.

## 3. Global assumptions (A)

Pending: A-1 (single actor — сотрудник отдела снабжения), A-2 (single warehouse /
складской список). See `docs/project-status.md`, Next step.

## 4. Definitions (D)

### D-1. Обработанное название

«Обработанное название — это введённое название без начальных и конечных пробелов».

## 5. Business rules (BR)

### BR-1

«Обработанное название (D-1) товара содержит хотя бы один символ».

### BR-2

«Обработанное название (D-1) товара не совпадает (без учёта регистра) ни с одним
названием товара из складского списка».

## 6. Functional requirements (FR)

### FR-1. Включить новый товар в список товаров на складе

Original wording: «включить новый товар в список товаров на складе».

«Сотрудник отдела снабжения вводит название товара. Введённое название обрабатывается
согласно D-1. Если нарушается BR-1 или BR-2 — операция отклоняется: складской список
не изменяется, выводится сообщение об ошибке, соответствующее нарушенному правилу.
Если BR-1 и BR-2 выполняются — в складской список добавляется товар: его обработанное
название (D-1) и количество, равное 0».

## 7. Accepted elaborations (принятые уточнения)

Decisions that go beyond the explicit text of the методичка (agreed during FR-1 review):

| ID | Decision | Agreed as |
|----|----------|-----------|
| EL-1 | Duplicate product names are rejected; the name is the product's unique identifier in the warehouse list | Q2 |
| EL-2 | A new product's quantity starts at 0; quantity changes belong to FR-5 | Q1 |
| EL-3 | Reject/error behavior, including a distinct error message per violated rule (the методичка describes no error scenarios) | Q6 |
| EL-4 | Name comparison is case-insensitive; the stored spelling is the first entered one (after trimming) | Q11 |
| EL-5 | Trimming of leading/trailing spaces (D-1); a whitespace-only name counts as empty and is rejected | Q5, Q9/Q10 |

## 8. Project extensions and future ideas

None at Phase 0. Everything beyond the original assignment scope will be recorded here,
clearly separated from Sections 2–7.
