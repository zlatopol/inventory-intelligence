"""CLI-меню «СНАБЖЕНИЕ» — третья дверь к тем же сервисам (после тестов и API).

Ни одной строки бизнес-логики: правила живут в сервисах (BR-1…BR-8),
CLI только спрашивает, показывает и ловит DomainError (EL-3-сообщения уже готовы).
Запуск: python -m app.cli
"""
from types import SimpleNamespace

from app.requests.schemas import _STATUS_RU  # DRY: перевод статусов уже существует
from app.shared.errors import DomainError


class ConsoleUI:
    """Тонкая обёртка над вводом/выводом — в тестах заменяется двойником."""

    def ask(self, prompt: str) -> str:
        return input(prompt)

    def say(self, message: str) -> None:
        print(message)


def ask_int(ui, prompt: str) -> int:
    """Механический парсинг ввода (Q3): бизнес-проверки — в сервисах."""
    while True:
        raw = ui.ask(prompt)
        try:
            return int(raw)
        except ValueError:
            ui.say(f"«{raw}» — не число, попробуйте ещё раз")


# --- Handlers: один пункт меню = один handler --------------------------------


def handle_add_product(ui, services) -> None:
    name = ui.ask("Название товара: ")                    # D-1 сделает сервис
    product = services.products.create_product(name)
    ui.say(f"→ Добавлен: {product.name} ({product.warehouse_quantity} шт.)")


def handle_receive_product(ui, services) -> None:
    name = ui.ask("Название товара: ")
    quantity = ask_int(ui, "Количество поступления: ")    # BR-5 проверит сервис
    product = services.products.receive_product(name, quantity)
    ui.say(f"→ Поступление учтено: {product.name} теперь {product.warehouse_quantity} шт.")


def handle_list_warehouse(ui, services) -> None:
    products = services.products.list_warehouse()
    if not products:
        ui.say("(склад пуст — это не ошибка, FR-6)")
        return
    for p in products:                                    # EL-10: порядок уже из SQL
        ui.say(f"  {p.name} — {p.warehouse_quantity} шт.")


# TODO (твоя работа, по образцу выше): реализуй эти handlers
def handle_delete_product(ui, services) -> None:
    # спросить название → services.products.delete_product(name) → «Удалён»
    name = ui.ask("Название товара: ")
    services.products.delete_product(name)   # None: ошибки, если будут, поймает цикл
    ui.say("→ Товар удалён из складского списка")



def handle_add_store(ui, services) -> None:
    # FR-3: services.stores.create_store(name)
    name = ui.ask("Название магазина: ")
    store = services.stores.create_store(name)
    ui.say(f"→ Добавлен магазин: {store.name}")


def handle_delete_store(ui, services) -> None:
    # FR-4: services.stores.delete_store(name)
    name = ui.ask("Название магазина: ")
    services.stores.delete_store(name)
    ui.say("→ Магазин удалён")

def handle_list_stores(ui, services) -> None:
    """FR-11: названия живых магазинов (порядок уже из SQL)."""
    stores = services.stores.list_stores()
    if not stores:
        ui.say("(магазинов нет — это не ошибка, FR-11)")
        return
    for store in stores:
        ui.say(f"  {store.name}")


def handle_submit_request(ui, services) -> None:
    """FR-8: магазин + товар + количество → заявка с номером."""
    store_name = ui.ask("Название магазина: ")
    product_name = ui.ask("Название товара: ")
    quantity = ask_int(ui, "Количество: ")  # BR-6 проверит сервис
    request = services.requests.submit_request(store_name, product_name, quantity)
    ui.say(f"→ Подана заявка №{request.number}")  # номер назначен сервисом после flush


def handle_process_request(ui, services) -> None:
    """FR-9: обработать заявку по номеру."""
    number = ask_int(ui, "Номер заявки: ")
    services.requests.process_request(number)
    ui.say(f"→ Заявка №{number} обработана")


def handle_list_requests(ui, services) -> None:
    """FR-10: все заявки по порядку номеров, статусы по-русски."""
    rows = services.requests.list_requests()
    if not rows:
        ui.say("(заявок нет — это не ошибка, FR-10)")
        return
    for request, store_name, product_name in rows:  # кортежи — распаковываем
        # после загрузки из БД status — обычная str (Mapped[str]);
        # StrEnum-ключи совместимы со str, .value не нужен
        status = _STATUS_RU[request.status]
        line = (
            f"№{request.number} [{status}] {store_name} — "
            f"{product_name}, {request.requested_quantity} шт."
        )
        if request.processed_at is not None:  # is None, не == (PEP8)
            line += f", обработана {request.processed_at:%Y-%m-%d}"
        ui.say(f"  {line}")


def handle_store_stock(ui, services) -> None:
    """FR-7: товары по магазинам — stock_by_store() возвращает СПИСОК кортежей
    (магазин, [(товар, количество), ...]) — порядок является частью контракта."""
    for store, items in services.stores.stock_by_store():
        ui.say(f"  {store.name}:")
        if not items:  # пустой магазин показывается, не прячется (EL-21)
            ui.say("    (нет товаров)")
        for product_name, quantity in items:
            ui.say(f"    {product_name} — {quantity} шт.")



MENU = {
    "1": ("Добавить товар", handle_add_product),
    "2": ("Удалить товар", handle_delete_product),
    "3": ("Поступление товара", handle_receive_product),
    "4": ("Добавить магазин", handle_add_store),
    "5": ("Удалить магазин", handle_delete_store),
    "6": ("Список магазинов", handle_list_stores),
    "7": ("Подать заявку", handle_submit_request),
    "8": ("Обработать заявку", handle_process_request),
    "9": ("Список заявок", handle_list_requests),
    "10": ("Товары на складе", handle_list_warehouse),
    "11": ("Товары по магазинам", handle_store_stock),
    "0": ("Выход", None),
}


def build_services(session) -> SimpleNamespace:
    """Сборка зависимостей — те же сервисы, что в провайдерах роутеров."""
    from app.events.repository import StockEventRepository
    from app.products.repository import ProductRepository
    from app.products.service import ProductService
    from app.requests.repository import StoreRequestRepository
    from app.requests.service import RequestService
    from app.stores.repository import StoreRepository
    from app.stores.service import StoreService

    return SimpleNamespace(
        products=ProductService(
            ProductRepository(session), StockEventRepository(session), session
        ),
        stores=StoreService(
            StoreRepository(session), StoreRequestRepository(session), session
        ),
        requests=RequestService(
            StoreRequestRepository(session),
            ProductRepository(session),
            StoreRepository(session),
            StockEventRepository(session),
            session,
        ),
    )


def main() -> None:
    from sqlalchemy.orm import sessionmaker

    from app.shared.db import get_engine

    ui = ConsoleUI()
    engine = get_engine()
    with sessionmaker(bind=engine, expire_on_commit=False)() as session:
        services = build_services(session)

        while True:
            ui.say("\n=== СНАБЖЕНИЕ — отдел снабжения оптовой базы ===")
            for key, (title, _) in MENU.items():
                ui.say(f"{key:>2}. {title}")
            choice = ui.ask("Выбор: ").strip()

            if choice == "0":
                break
            entry = MENU.get(choice)
            if entry is None:
                ui.say("Нет такого пункта")
                continue
            try:
                entry[1](ui, services)  # Q1: DomainError ловится здесь, один раз
            except DomainError as exc:
                ui.say(f"! {exc}")
            except (KeyboardInterrupt, EOFError):
                ui.say("\nВыход.")
                break


if __name__ == "__main__":
    main()