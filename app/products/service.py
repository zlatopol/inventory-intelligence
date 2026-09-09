from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.products.models import Product
from app.products.repository import ProductRepository
from app.shared.errors import (
    DuplicateProductNameError,
    EmptyNameError,
    InvalidReceiptQuantityError,
    ProductDeletionBlockedError,
    ProductNotFoundError,
)


def _is_positive_integer(quantity: int) -> bool:
    # bool is an int subclass in Python — exclude it explicitly (True == 1).
    return isinstance(quantity, int) and not isinstance(quantity, bool) and quantity > 0


class ProductService:
    """Product use cases: FR-1, FR-2, FR-5, FR-6.

    Transaction owner per ADR-0003: mutating use cases commit here.
    """

    def __init__(self, repository: ProductRepository, session: Session) -> None:
        self._repo = repository
        self._session = session

    def create_product(self, raw_name: str) -> Product:
        """FR-1: включить новый товар в список товаров на складе."""
        name = raw_name.strip()  # D-1
        if not name:
            raise EmptyNameError  # BR-1
        if self._repo.find_live_by_name(name) is not None:
            raise DuplicateProductNameError  # BR-2 (deterministic friendly check)

        product = Product(name=name, warehouse_quantity=0)  # EL-2: starts at 0
        self._repo.add(product)
        try:
            self._session.flush()
        except IntegrityError:
            # ADR-0004: the partial unique index won a race with us —
            # same user-facing outcome as the BR-2 check above.
            self._session.rollback()
            raise DuplicateProductNameError from None
        self._session.commit()
        return product

    def delete_product(self, raw_name: str) -> None:
        """FR-2: удалить ненужный товар из складского списка (soft delete, ADR-0005)."""
        name = raw_name.strip()
        if not name:
            raise EmptyNameError
        product = self._get_live_or_raise(name)
        if product.warehouse_quantity != 0:
            raise ProductDeletionBlockedError  # BR-3
        product.deleted_at = datetime.now(UTC)
        self._session.commit()

    def receive_product(self, raw_name: str, quantity: int) -> Product:
        """FR-5: учесть поступление некоторого товара на склад."""
        name = raw_name.strip()
        if not name:
            raise EmptyNameError
        if not _is_positive_integer(quantity):
            raise InvalidReceiptQuantityError  # BR-5
        product = self._get_live_or_raise(name)
        product.warehouse_quantity += quantity
        self._session.commit()
        return product

    def list_warehouse(self) -> Sequence[Product]:
        """FR-6: просмотреть информацию о товарах на складе."""
        return self._repo.list_live_ordered_by_name()

    def _get_live_or_raise(self, name: str) -> Product:
        product = self._repo.find_live_by_name(name)
        if product is None:
            raise ProductNotFoundError
        return product
