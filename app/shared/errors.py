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
