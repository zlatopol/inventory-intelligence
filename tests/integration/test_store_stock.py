"""Integration tests: FR-7 per-store stock view (stores repository/service)."""
from app.products.models import Product
from app.requests.models import StoreProduct
from app.stores.models import Store
from app.stores.repository import StoreRepository
from app.stores.service import StoreService


def add_product(session, name: str, warehouse_quantity: int = 10) -> Product:
    product = Product(name=name, warehouse_quantity=warehouse_quantity)
    session.add(product)
    session.flush()
    return product


def add_store(session, name: str) -> Store:
    store = Store(name=name)
    session.add(store)
    session.flush()
    return store


def add_stock(session, store: Store, product: Product, quantity: int) -> None:
    session.add(
        StoreProduct(store_id=store.id, product_id=product.id, quantity=quantity)
    )
    session.flush()


def test_grouping_and_two_level_ordering(db_session):
    """EL-21: магазины по алфавиту, товары внутри — по алфавиту (без регистра)."""
    ashan = add_store(db_session, "ашан")
    magnit = add_store(db_session, "Магнит")
    sugar = add_product(db_session, "Сахар")
    apples = add_product(db_session, "Яблоки")
    add_stock(db_session, magnit, sugar, 5)
    add_stock(db_session, magnit, apples, 2)
    add_stock(db_session, ashan, sugar, 1)
    db_session.expire_all()

    result = StoreService(
        StoreRepository(db_session), None, db_session  # type: ignore[arg-type]
    ).stock_by_store()

    assert [(s.name, items) for s, items in result] == [
        ("ашан", [("Сахар", 1)]),
        ("Магнит", [("Сахар", 5), ("Яблоки", 2)]),  # С < Я: товары по алфавиту
    ]


def test_empty_store_displayed_with_empty_list(db_session):
    """EL-21: магазин без товаров показывается с пустым списком, не прячется."""
    add_store(db_session, "Пустой")
    add_store(db_session, "Складской")
    sugar = add_product(db_session, "Сахар")
    add_stock(db_session, db_session.scalars(
        __import__("sqlalchemy", fromlist=["select"]).select(Store).where(
            Store.name == "Складской"
        )
    ).first(), sugar, 3)
    db_session.expire_all()

    result = StoreService(
        StoreRepository(db_session), None, db_session  # type: ignore[arg-type]
    ).stock_by_store()

    mapping = {s.name: items for s, items in result}
    assert mapping["Пустой"] == []  # показан, пустой
    assert mapping["Складской"] == [("Сахар", 3)]


def test_delisted_product_still_shown_in_stores(db_session):
    """EL-22 (главный тест среза): товар удалён из складского списка (FR-2),
    но остаток в магазине жив — FR-7 показывает его."""
    store = add_store(db_session, "Магнит")
    sugar = add_product(db_session, "Сахар", warehouse_quantity=0)
    add_stock(db_session, store, sugar, 4)
    sugar.deleted_at = sugar.created_at  # soft delete: delisted (ADR-0005)
    db_session.flush()
    db_session.expire_all()

    result = StoreService(
        StoreRepository(db_session), None, db_session  # type: ignore[arg-type]
    ).stock_by_store()

    assert result[0][1] == [("Сахар", 4)]  # физическая реальность, не ассортимент


def test_deleted_store_not_shown(db_session):
    """Магазин удалён (FR-4) — из FR-7 исчезает целиком."""
    store = add_store(db_session, "Магнит")
    sugar = add_product(db_session, "Сахар")
    add_stock(db_session, store, sugar, 4)
    store.deleted_at = store.created_at
    db_session.flush()
    db_session.expire_all()

    result = StoreService(
        StoreRepository(db_session), None, db_session  # type: ignore[arg-type]
    ).stock_by_store()

    assert result == []
