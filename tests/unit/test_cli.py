"""Unit tests for the CLI menu — ui-двойник вместо input/print, фейки вместо сервисов.

Тестируется Presentation-слой: что CLI спросил, что передал в сервис, что показал.
Бизнес-правила уже охраняются 92 тестами сервисов — здесь их НЕ дублируем.
"""
from datetime import date
from types import SimpleNamespace

from app.cli import MENU, handle_add_product, run_menu
from app.shared.errors import InvalidReplenishmentWindowError


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
        self.id_calls: list[str] = []
        self._product = SimpleNamespace(name="Сахар", warehouse_quantity=0)

    def create_product(self, name: str):
        self.create_calls.append(name)
        return self._product

    def get_live_id_by_name(self, name: str) -> int:
        self.id_calls.append(name)
        return 42  # int, как настоящий


class FakeStores:
    """Двойник StoreService: помнит вызовы, возвращает id."""

    def __init__(self) -> None:
        self.id_calls: list[str] = []

    def get_live_id_by_name(self, name: str) -> int:
        self.id_calls.append(name)
        return 7  # int, как настоящий


class FakeForecast:
    """Двойник ForecastService: помнит вызовы, возвращает заготовку."""

    def __init__(self, result: dict | None = None) -> None:
        self.calls: list[tuple] = []
        self._result = result

    def forecast(self, store_id: int, product_id: int, days: int) -> dict:
        self.calls.append((store_id, product_id, days))
        return self._result


class FailingForecast(FakeForecast):
    """Двойник, чей forecast бросает LookupError (пары нет в истории)."""

    def forecast(self, store_id: int, product_id: int, days: int) -> dict:
        raise LookupError("В истории событий нет пары store=7, product=42")


class FakeRecommendations:
    """Двойник RecommendationService: помнит вызовы, возвращает заготовку."""

    def __init__(self, result: dict | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result

    def recommendations(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self._result


class FailingRecommendations(FakeRecommendations):
    """Двойник, чей recommendations бросает DomainError (плохие параметры)."""

    def recommendations(self, **kwargs) -> dict:
        raise InvalidReplenishmentWindowError(8, 7, 14)


def make_services(
    products=None, stores=None, forecast=None, recommendations=None
) -> SimpleNamespace:
    return SimpleNamespace(
        products=products or FakeProducts(),
        stores=stores or FakeStores(),
        requests=object(),
        forecast=forecast or FakeForecast(),
        recommendations=recommendations or FakeRecommendations(),
    )


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



def test_ask_int_repeats_prompt_on_garbage_then_accepts_number():
    """Мусорный ввод повторяет вопрос, затем число принимается."""
    ui = FakeUI(["abc", "7"])

    from app.cli import ask_int

    value = ask_int(ui, "Введите число: ")

    assert value == 7
    assert "не число" in ui.text()


def test_run_menu_unknown_choice_keeps_menu_alive():
    """Неизвестный пункт не роняет меню — оно продолжает работу."""
    ui = FakeUI(["99", "0"])
    products = FakeProducts()

    run_menu(ui, make_services(products))

    assert "Нет такого пункта" in ui.text()
    assert products.create_calls == []  # ничего не вызывалось


class FailingProducts(FakeProducts):
    """Фейк, чей create_product бросает доменную ошибку."""

    def create_product(self, name: str):
        from app.shared.errors import DuplicateProductNameError

        raise DuplicateProductNameError()


def test_run_menu_domain_error_prints_message_and_survives():
    """DomainError печатается как «! …», цикл меню доживает до выхода."""
    ui = FakeUI(["1", "Сахар", "0"])

    run_menu(ui, make_services(FailingProducts()))

    assert "! Товар с таким названием уже есть" in ui.text()
    assert "Выход" in ui.text() or ui.text().count("Выбор") >= 2  # меню продолжилось


def test_run_menu_zero_exits_without_service_calls():
    """Выбор «0» завершает меню, не трогая сервисы."""
    ui = FakeUI(["0"])
    products = FakeProducts()

    run_menu(ui, make_services(products))

    assert products.create_calls == []  # главное утверждение
    assert ui.text().count("СНАБЖЕНИЕ") == 1  # меню отрисовалось ровно один раз


def test_menu_has_twelve_operations_plus_exit_with_distinct_handlers():
    """Меню покрывает все 13 операций + выход; хэндлеры не дублируются."""
    assert len(MENU) == 14
    assert MENU["0"] == ("Выход", None)

    handlers = [handler for _, (_, handler) in MENU.items() if handler is not None]
    assert len(handlers) == 13
    assert len(set(handlers)) == 13  # дубль handler'а сломал бы эту строку

# --- Прогноз (пункт 12) -------------------------------------------------------


def test_forecast_handler_resolves_names_and_prints_days_and_model():
    """Пункт 12: имена → id → forecast(store, product, days); вывод — дни+модель."""
    # ARRANGE: диалог = выбор пункта, ответы handler'а, выход
    ui = FakeUI(["12", "  Магазин А ", "Товар Б", "3", "0"])
    forecast = FakeForecast(
        result={
            "store_id": 7,
            "product_id": 42,
            "generated_at": date(2026, 10, 12),
            "model": "lightgbm",
            "warning": None,
            "forecast": [
                {"date": date(2026, 10, 13), "demand": 15.5},
                {"date": date(2026, 10, 14), "demand": 18.0},
            ],
        }
    )
    services = make_services(forecast=forecast)

    # ACT
    run_menu(ui, services)

    # ASSERT: резолв по именам, сервис получил именно id и горизонт
    assert services.stores.id_calls == ["  Магазин А "]  # сырой ввод — D-1 в сервисе
    assert services.products.id_calls == ["Товар Б"]
    assert forecast.calls == [(7, 42, 3)]

    # ASSERT: пользователь увидел прогноз и метку модели
    assert "на 3 дня" in ui.text()
    assert "модель: lightgbm" in ui.text()
    assert "2026-10-13 — 15.5 шт." in ui.text()
    assert "2026-10-14 — 18.0 шт." in ui.text()


def test_forecast_handler_lookup_error_prints_and_menu_survives():
    """Пары нет в истории: LookupError печатается локально, меню доживает до выхода."""
    ui = FakeUI(["12", "Магазин А", "Товар Б", "3", "0"])
    services = make_services(forecast=FailingForecast())

    # ACT
    run_menu(ui, services)

    # ASSERT: сообщение видно И меню пережило ошибку (отрисовалось снова)
    assert "! В истории событий нет пары" in ui.text()
    assert ui.text().count("СНАБЖЕНИЕ") >= 2


# --- Рекомендации (пункт 13) ---------------------------------------------------


def make_recommendation_result() -> dict:
    return {
        "generated_at": date(2026, 10, 14),
        "service_level": 0.95,
        "lead_time_days": 3,
        "horizon_days": 7,
        "warning": None,
        "recommendations": [
            {
                "product_id": 1,
                "product_name": "Сахар",
                "status": "order",
                "warehouse_quantity": 10,
                "forecast_demand": 40.0,
                "safety_stock": 12.3,
                "order_quantity": 43,
                "model": "lightgbm",
            },
            {
                "product_id": 2,
                "product_name": "Соль",
                "status": "sufficient",
                "warehouse_quantity": 100,
                "forecast_demand": 40.0,
                "safety_stock": 12.3,
                "order_quantity": 0,
                "model": "lightgbm",
            },
            {
                "product_id": 3,
                "product_name": "Кофе",
                "status": "cold_start",
                "warehouse_quantity": 5,
                "forecast_demand": None,
                "safety_stock": None,
                "order_quantity": None,
                "model": None,
            },
        ],
    }


def test_recommendations_handler_empty_inputs_use_defaults():
    """Пункт 13: три пустых ввода → дефолты 0.95/3/7 уходят в сервис одним вызовом."""
    ui = FakeUI(["13", "", "", "", "0"])
    recommendations = FakeRecommendations(result=make_recommendation_result())
    services = make_services(recommendations=recommendations)

    run_menu(ui, services)

    assert recommendations.calls == [
        {
            "service_level": 0.95,
            "lead_time_days": 3,
            "horizon_days": 7,
        }
    ]
    # вывод: все три ветки статуса читаемы
    assert "заказать 43 шт." in ui.text()
    assert "достаточно" in ui.text()
    assert "холодный старт" in ui.text()
    assert "на окно 10 дней" in ui.text()


def test_recommendations_handler_custom_params_passed_through():
    ui = FakeUI(["13", "0.99", "5", "9", "0"])
    recommendations = FakeRecommendations(result=make_recommendation_result())
    services = make_services(recommendations=recommendations)

    run_menu(ui, services)

    assert recommendations.calls == [
        {"service_level": 0.99, "lead_time_days": 5, "horizon_days": 9}
    ]
    assert "на окно 14 дней" in ui.text()


def test_recommendations_handler_domain_error_prints_and_menu_survives():
    """Плохие параметры: DomainError ловится общим catch меню, диалог живёт."""
    ui = FakeUI(["13", "0.95", "8", "7", "0"])  # L+H = 15 > 14
    services = make_services(recommendations=FailingRecommendations())

    run_menu(ui, services)

    assert "! Сумма времени поставки и горизонта обзора" in ui.text()
    assert ui.text().count("СНАБЖЕНИЕ") >= 2
