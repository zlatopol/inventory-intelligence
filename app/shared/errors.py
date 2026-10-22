class DomainError(Exception):
    """Base class for domain errors mapped to API responses."""


class EmptyNameError(DomainError):
    def __init__(self) -> None:
        super().__init__("Название не должно быть пустым после удаления начальных и конечных пробелов (BR-1)")


class DuplicateProductNameError(DomainError):
    def __init__(self) -> None:
        super().__init__("Товар с таким названием уже есть в складском списке (BR-2)")


class ProductNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Товар с таким названием не найден в складском списке")


class ProductDeletionBlockedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Нельзя удалить товар: его количество на складе не равно нулю (BR-3)")


class InvalidReceiptQuantityError(DomainError):
    def __init__(self) -> None:
        super().__init__("Количество поступления должно быть целым числом, большим нуля (BR-5)")


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
        super().__init__("Количество запрашиваемого товара — целое число, большее нуля (BR-6)")


class RequestNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Заявка с таким номером не найдена")


class RequestAlreadyProcessedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Заявка уже обработана")


class InsufficientStockError(DomainError):
    def __init__(self) -> None:
        super().__init__("Количество товара на складе меньше количества заявки (BR-7)")


class InvalidSaleQuantityError(DomainError):
    def __init__(self) -> None:
        super().__init__("Количество продажи должно быть целым числом, большим нуля")


class InsufficientStoreStockError(DomainError):
    def __init__(self) -> None:
        super().__init__("Недостаточный остаток товара в магазине для продажи или отмены")


class SaleNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__("Продажа не найдена")


class SaleAlreadyReversedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Эта продажа уже отменена")


class IdempotencyConflictError(DomainError):
    def __init__(self) -> None:
        super().__init__("Ключ повторного запроса пустой или уже использован для другой операции")


class InvalidForecastHorizonError(DomainError):
    def __init__(self, days: int, min_days: int, max_days: int) -> None:
        super().__init__(f"Горизонт прогноза — целое число от {min_days} до {max_days} дней (получено: {days})")


class InvalidServiceLevelError(DomainError):
    def __init__(self, service_level: float) -> None:
        super().__init__(f"Уровень сервиса — число строго между 0 и 1 (получено: {service_level})")


class InvalidLeadTimeError(DomainError):
    def __init__(self, lead_time_days: int) -> None:
        super().__init__(f"Время поставки — целое число дней, не меньше 1 (получено: {lead_time_days})")


class InvalidPolicyHorizonError(DomainError):
    def __init__(self, horizon_days: int) -> None:
        super().__init__(f"Горизонт обзора — целое число дней, не меньше 1 (получено: {horizon_days})")


class InvalidReplenishmentWindowError(DomainError):
    def __init__(self, lead_time_days: int, horizon_days: int, max_window: int) -> None:
        super().__init__(
            f"Сумма времени поставки и горизонта обзора не должна превышать {max_window} дней "
            f"— доказанный горизонт модели (получено: {lead_time_days} + {horizon_days})"
        )
