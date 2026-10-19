#!/bin/bash
# Live demo: the full assignment scenario (FR-1 … FR-11) against a running API.
#
# Usage:
#   .venv/bin/uvicorn app.main:app --port 8000   # in one terminal
#   scripts/demo.sh                               # in another
#
# Assumes a clean database. To reset:
#   docker compose exec db psql -U inventory -d inventory \
#     -c 'TRUNCATE store_request, store_product, product, store RESTART IDENTITY;
#         ALTER SEQUENCE store_request_number_seq RESTART;'

set -euo pipefail
BASE="${BASE_URL:-http://127.0.0.1:8000}"
PY=".venv/bin/python"

req()  { curl -s -X "$1" "$BASE$2" ${3:+-H 'Content-Type: application/json' -d "$3"}; }
show() { echo "  → $1"; }
code() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" ${3:+-H 'Content-Type: application/json' -d "$3"}; }
number() { $PY -c "import sys,json;print(json.load(sys.stdin)['number'])"; }

echo '── FR-1: включить товары (D-1: trim; EL-4: первое написание)'
show "$(req POST /api/products '{"name": "  Молоко  "}')"          # → «Молоко»
show "$(req POST /api/products '{"name": "Сахар"}')"
echo '  BR-2: дубликат без учёта регистра:'
show "$(code POST /api/products '{"name": "молоко"}')"              # → 409

echo '── FR-3: включить магазины'
show "$(req POST /api/stores '{"name": "Магнит"}')"
show "$(req POST /api/stores '{"name": "Пятёрочка"}')"

echo '── FR-6: просмотр склада (пустой — валиден, но тут уже товары)'
show "$(req GET /api/products)"

echo '── FR-5: учесть поступления'
show "$(req POST /api/products/Сахар/receipts  '{"quantity": 100}')"
show "$(req POST /api/products/Молоко/receipts '{"quantity": 50}')"

echo '── FR-8: подать заявки (EL-12: остаток не проверяется при подаче)'
N1=$(req POST /api/requests '{"store_name": "Магнит",     "product_name": "Сахар",  "quantity": 30}'  | number)
N2=$(req POST /api/requests '{"store_name": "Пятёрочка",  "product_name": "Молоко", "quantity": 10}'  | number)
N3=$(req POST /api/requests '{"store_name": "Магнит",     "product_name": "Сахар",  "quantity": 500}' | number)
echo "  → поданы №$N1, №$N2, №$N3 (№$N3 — обречённая: 500 > остатка)"

echo '── FR-10: просмотр заявок (статусы по-русски, EL-15/EL-20)'
show "$(req GET /api/requests)"

echo '── FR-4 + BR-8: удаление магазина с заявкой «подана»'
show "$(code DELETE /api/stores/Магнит)"                           # → 409

echo '── FR-9: обработать заявки (EL-17: три изменения атомарно)'
show "$(req POST "/api/requests/$N1/process")"                     # склад 100→70, Магнит: Сахар 30
show "$(req POST "/api/requests/$N2/process")"                     # склад 50→40, Пятёрочка: Молоко 10
echo "  BR-7: нехватка остатка для №$N3:"
show "$(code POST "/api/requests/$N3/process")"                    # → 409, ничего не изменилось

echo '── FR-7: товары по магазинам (EL-21/EL-22)'
show "$(req GET /api/stores/stock)"

echo '── FR-6: склад после отгрузок'
show "$(req GET /api/products)"

echo '── FR-2 + BR-3: удаление товара с ненулевым остатком'
show "$(code DELETE /api/products/Молоко)"                         # → 409 (40 кг на складе)

echo '── FR-4 + EL-19: удаление магазина только с обработанными заявками'
show "$(code DELETE /api/stores/Пятёрочка)"                        # → 204

echo "── FR-10 (финал): №$N3 всё ещё «подана» — история и потребность сохранены"
show "$(req GET /api/requests)"
echo '── FR-7 (финал): Пятёрочки нет, Магнит с остатками'
show "$(req GET /api/stores/stock)"
