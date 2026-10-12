class DomainError(Exception):
    """Base class for domain errors.

    Subtypes carry distinct user-facing messages (EL-3: one message per violated
    rule); the API layer maps them to HTTP 4xx responses.
    """


class EmptyNameError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Название не должно быть пустым после удаления начальных и конечных "
            "пробелов (BR-1)"
        )


class DuplicateProductNameError(DomainError):
    def __init__(self) -> None:
        super().__init__("Товар с таким названием уже есть в складском списке (BR-2)")


class ProductNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Товар с таким названием не найден в складском списке")


class ProductDeletionBlockedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Нельзя удалить товар: его количество на складе не равно нулю (BR-3)"
        )


class InvalidReceiptQuantityError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Количество поступления должно быть целым числом, большим нуля (BR-5)"
        )


class DuplicateStoreNameError(DomainError):
    def __init__(self) -> None:
        super().__init__("Магазин с таким названием уже есть в списке магазинов (BR-4)")


class StoreNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Магазин с таким названием не найден в списке магазинов")

class StoreDeletionBlockedError(DomainError):
    def __init__(self) -> None:
        super().__init__("У магазина есть заявки со статусом «подана» (BR-8)")

class InvalidRequestQuantityError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Количество запрашиваемого товара — целое число, большее нуля (BR-6)"
        )


class RequestNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Заявка с таким номером не найдена")


class RequestAlreadyProcessedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Заявка уже обработана")


class InsufficientStockError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "Количество товара на складе меньше количества заявки (BR-7)"
        )


class InvalidForecastHorizonError(DomainError):
    def __init__(self, days: int, min_days: int, max_days: int) -> None:
        super().__init__(
            f"Горизонт прогноза — целое число от {min_days} до {max_days} дней "
            f"(получено: {days})"
        )
