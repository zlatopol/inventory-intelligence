"""Unit tests for the CLI menu — ui-двойник вместо input/print, фейки вместо сервисов.

Тестируется Presentation-слой: что CLI спросил, что передал в сервис, что показал.
Бизнес-правила уже охраняются 92 тестами сервисов — здесь их НЕ дублируем.
"""
from types import SimpleNamespace

from app.cli import handle_add_product, run_menu, MENU


class FakeUI:
    """Двойник ConsoleUI: ответы подаются списком, вывод собирается для assert."""

    def __init__(self, answers: list[str]) -> None:
        self._answers = iter(answers)
        self.output: list[str] = []

    def ask(self, prompt: str) -> str:
        return next(self._answers)

    def say(self, message: str) -> None:
        self.output.append(message)

    def text(self) -> str:
        return "\n".join(self.output)


class FakeProducts:
    """Двойник ProductService: помнит вызовы, возвращает заготовку."""

    def __init__(self) -> None:
        self.create_calls: list[str] = []
        self._product = SimpleNamespace(name="Сахар", warehouse_quantity=0)

    def create_product(self, name: str):
        self.create_calls.append(name)
        return self._product


def make_services(products=None) -> SimpleNamespace:
    return SimpleNamespace(
        products=products or FakeProducts(),
        stores=object(),
        requests=object(),
    )


# --- ОБРАЗЕЦ (разбери его структуру: ARRANGE → ACT → ASSERT) -----------------


def test_add_product_passes_raw_input_and_prints_product():
    # ARRANGE: двойники с заготовленным вводом
    ui = FakeUI(["  Сахар  "])
    products = FakeProducts()
    services = make_services(products)

    # ACT: один handler
    handle_add_product(ui, services)

    # ASSERT: сервис получил СЫРОЙ ввод (trim — работа сервиса, D-1);
    # пользователю показали имя из ответа сервиса и стартовое количество
    assert products.create_calls == ["  Сахар  "]
    assert "Сахар" in ui.text()
    assert "0 шт." in ui.text()


# --- ТВОИ ТЕСТЫ (переписаны по ревью: имена = поведение) ----------------------


def test_ask_int_repeats_prompt_on_garbage_then_accepts_number():
    # TODO 1: ask_int повторяет вопрос при «abc», затем принимает число
    ui = FakeUI(["abc", "7"])

    from app.cli import ask_int

    value = ask_int(ui, "Введите число: ")

    assert value == 7
    assert "не число" in ui.text()


def test_run_menu_unknown_choice_keeps_menu_alive():
    # TODO 2: выбор «99» → «Нет такого пункта», меню продолжает работу
    ui = FakeUI(["99", "0"])
    products = FakeProducts()

    run_menu(ui, make_services(products))

    assert "Нет такого пункта" in ui.text()
    assert products.create_calls == []  # ничего не вызывалось


class FailingProducts(FakeProducts):
    """Фейк, чей create_product бросает доменную ошибку (для TODO 3)."""

    def create_product(self, name: str):
        from app.shared.errors import DuplicateProductNameError

        raise DuplicateProductNameError()


def test_run_menu_domain_error_prints_message_and_survives():
    # TODO 3: DomainError → «! …», цикл живёт и доходит до выхода
    ui = FakeUI(["1", "Сахар", "0"])

    run_menu(ui, make_services(FailingProducts()))

    assert "! Товар с таким названием уже есть" in ui.text()
    assert "Выход" in ui.text() or ui.text().count("Выбор") >= 2  # меню продолжилось


def test_run_menu_zero_exits_without_service_calls():
    # TODO 4: «0» → выход, сервисы не тронуты
    ui = FakeUI(["0"])
    products = FakeProducts()

    run_menu(ui, make_services(products))

    assert products.create_calls == []  # главное утверждение
    assert ui.text().count("СНАБЖЕНИЕ") == 1  # меню отрисовалось ровно один раз


def test_menu_has_eleven_operations_plus_exit_with_distinct_handlers():
    # TODO 5: 11 операций + выход; handlers различны (set ловит дубликаты)
    assert len(MENU) == 12
    assert MENU["0"] == ("Выход", None)

    handlers = [handler for _, (_, handler) in MENU.items() if handler is not None]
    assert len(handlers) == 11
    assert len(set(handlers)) == 11  # дубль handler'а сломал бы эту строку