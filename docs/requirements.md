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
| FR-2 | «удалить ненужный товар из складского списка» | **Accepted** |
| FR-3 | «включить новый магазин в список магазинов» | **Accepted** |
| FR-4 | «удалить ненужный магазин из списка» | Pending |
| FR-5 | «учесть поступление некоторого товара на склад» | Pending |
| FR-6 | «просмотреть информацию о товарах на складе» | Pending |
| FR-7 | «просмотреть информацию о товарах по магазинам» | Pending |

Note: store requests («заявки магазинов на текущий год») appear in the assignment's domain
description but are not among the seven operations — to be discussed separately after FR-7.

## 3. Global assumptions (A)

### A-1

«Единственный пользователь системы — сотрудник отдела снабжения оптовой базы».

### A-2

«Оптовая база имеет один склад; товары на складе образуют складской список».

## 4. Definitions (D)

### D-1. Обработанное название

«Обработанное название — это введённое название без начальных и конечных пробелов».

## 5. Business rules (BR)

### BR-1

«Обработанное название (D-1) содержит хотя бы один символ».

*Редакция 2 (2026-09-07, FR-3): обобщено — слово «товара» убрано, правило применяется
ко всем названиям (товар, магазин). Редакция 1 (FR-1): «Обработанное название (D-1)
товара содержит хотя бы один символ».*

### BR-2

«Обработанное название (D-1) товара не совпадает (без учёта регистра) ни с одним
названием товара из складского списка».


### BR-4

«Обработанное название (D-1) магазина не совпадает (без учёта регистра) ни с одним
названием магазина из списка магазинов».
### BR-3

«Товар может быть удалён из складского списка, только если его количество на складе
равно нулю».

## 6. Functional requirements (FR)

### FR-1. Включить новый товар в список товаров на складе

Original wording: «включить новый товар в список товаров на складе».


### FR-2. Удалить ненужный товар из складского списка

Original wording: «удалить ненужный товар из складского списка».

«Сотрудник отдела снабжения (A-1) вводит название товара. Введённое название
обрабатывается согласно D-1. Если нарушается BR-1 — операция отклоняется. В складском
списке ищется товар, чьё название совпадает с обработанным введённым названием
(без учёта регистра). Если такой товар не найден — операция отклоняется. Если товар

### FR-3. Включить новый магазин в список магазинов

Original wording: «включить новый магазин в список магазинов».

«Сотрудник отдела снабжения (A-1) вводит название магазина. Введённое название
обрабатывается согласно D-1. Если нарушается BR-1 или BR-4 — операция отклоняется:
список магазинов не изменяется, выводится сообщение об ошибке, соответствующее
нарушенному правилу. Если BR-1 и BR-4 выполняются — в список магазинов добавляется
магазин: его обработанное название (D-1)».

Примечание: на Phase 0 магазин имеет только название — других атрибутов методичка
не требует. Дополнительные атрибуты могут появиться только как отдельное решение
(extensions / future ideas), а не как молчаливое расширение FR-3.
найден, но нарушается BR-3 — операция отклоняется. Во всех случаях отказа складской
список не изменяется, выводится сообщение об ошибке, соответствующее причине отказа.
Если товар найден и BR-3 выполняется — товар удаляется из складского списка».

Примечание: «ненужный» в формулировке операции — решение актёра, системой не проверяется.
«Сотрудник отдела снабжения (A-1) вводит название товара. Введённое название обрабатывается
согласно D-1. Если нарушается BR-1 или BR-2 — операция отклоняется: складской список| EL-6 | Deletion from the warehouse list is allowed only when the product's warehouse quantity is zero (BR-3) | FR-2, Q3 |
| EL-7 | Operational failure «товар не найден» when the entered name matches no product in the warehouse list; own error message, list unchanged | FR-2, Q1–Q2 |не изменяется, выводится сообщение об ошибке, соответствующее нарушенному правилу.
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
