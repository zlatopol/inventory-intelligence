# scripts/seed.py
"""Seed: генерирует ~8 недель правдоподобной истории через НАШИ сервисы.

Никакого прямого SQL для заявок: каждый шаг проходит BR-проверки и оставляет
согласованные события. Компромисс Q2(a) из брифа: append-only — дисциплина
продакшен-записи; seed СОЗНАТЕЛЬНО правит только МЕТКИ ВРЕМЕНИ (не состав!)
событий и заявок, созданных валидным путём. Q3: random.seed — воспроизводимость.

Запуск: .venv/bin/python scripts/seed.py  (БД должна быть чиста)
"""
import random
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

# Project root on sys.path (like migrations/env.py): `python scripts/seed.py`
# puts only scripts/ on the path, not the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cli import build_services  # noqa: E402
from app.events.models import StockEvent  # noqa: E402
from app.shared.db import get_engine  # noqa: E402

WEEKDAY_FACTOR = {"пн": 1, "вт": 1, "ср": 1, "чт": 1, "пт": 1.2, "сб": 1.5, "вс": 1.5}
DAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
PRODUCT_NAMES = ["Молоко", "Хлеб", "Сахар", "Кофе"]
STORE_NAMES = ["Ашан", "Лента", "Перекресток"]
BASE = 15
WEEKS = 8


def demand_qty(day: date) -> int:
    """base × сезонность_дня × (1 + шум); ≥ 1 (BR-6), целое (round)."""
    factor = WEEKDAY_FACTOR[DAYS[day.weekday()]]
    return max(1, round(BASE * factor * (1 + random.gauss(0, 0.15))))


def seed_timestamp(day: date) -> datetime:
    """Момент внутри дня (8–20 ч, UTC) — события одного дня различаются."""
    return datetime(
        day.year, day.month, day.day,
        random.randint(8, 20), random.randint(0, 59), tzinfo=UTC,
    )


def main() -> None:
    random.seed(42)  # Q3: воспроизводимость

    engine = get_engine()
    start_date = date.today() - timedelta(weeks=WEEKS)
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        services = build_services(session)

        product_ids = {
            name: services.products.create_product(name).id for name in PRODUCT_NAMES
        }
        for store_name in STORE_NAMES:
            services.stores.create_store(store_name)

        # (день, товар, магазин) → количество; пополнение — на каждый день
        demand: dict[tuple[date, str, str], int] = {}
        event_backdate: list[tuple[int, datetime]] = []  # (stock_event.id, метка)
        for day_offset in range(WEEKS * 7):
            day = start_date + timedelta(days=day_offset)
            for product_name in PRODUCT_NAMES:
                day_total = 0
                for store_name in STORE_NAMES:
                    qty = demand_qty(day)
                    demand[(day, product_name, store_name)] = qty
                    day_total += qty
                # пополнение в начале дня с запасом 1.5 — BR-7 не заблокирует
                services.products.receive_product(product_name, round(day_total * 1.5))
                receipt = session.execute(
                    select(StockEvent)
                    .where(
                        StockEvent.product_id == product_ids[product_name],
                        StockEvent.event_type == "receipt",
                    )
                    .order_by(StockEvent.id.desc())
                ).scalars().first()
                event_backdate.append((receipt.id, seed_timestamp(day)))

        # заявки: подать → обработать (shipment) → запомнить метку
        request_backdate: list[tuple[int, datetime]] = []  # (number, метка)
        for (day, product_name, store_name), quantity in demand.items():
            request = services.requests.submit_request(store_name, product_name, quantity)
            services.requests.process_request(request.number)
            shipment = session.execute(
                select(StockEvent).where(StockEvent.request_number == request.number)
            ).scalar_one()  # снимок номера (ADR-0006 Q2) находит событие
            ts = seed_timestamp(day)
            event_backdate.append((shipment.id, ts))
            request_backdate.append((request.number, ts))

        # Q2(a): правим ТОЛЬКО метки времени — состав создан валидными путями
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE stock_event SET occurred_at = :ts WHERE id = :id"),
                [{"id": eid, "ts": ts} for eid, ts in event_backdate],
            )
            conn.execute(
                text(
                    "UPDATE store_request "
                    "SET submitted_at = :ts, processed_at = :ts WHERE number = :n"
                ),
                [{"n": n, "ts": ts} for n, ts in request_backdate],
            )

    total_shipments = WEEKS * 7 * len(PRODUCT_NAMES) * len(STORE_NAMES)
    print(f"Seeded {total_shipments} shipments over {WEEKS} weeks.")


if __name__ == "__main__":
    main()