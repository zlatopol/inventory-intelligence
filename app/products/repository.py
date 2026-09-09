from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.products.models import Product


class ProductRepository:
    """Data access for the product aggregate.

    No business decisions, no transaction management (ADR-0003): the owning
    service flushes/commits the shared session.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def find_live_by_name(self, name: str) -> Product | None:
        """Case-insensitive lookup among live (non-deleted) products."""
        stmt = select(Product).where(
            Product.deleted_at.is_(None),
            func.lower(Product.name) == name.lower(),
        )
        return self._session.scalars(stmt).first()

    def add(self, product: Product) -> Product:
        self._session.add(product)
        return product

    def list_live_ordered_by_name(self) -> Sequence[Product]:
        """FR-6: live products, alphabetical by name, case-insensitive (EL-10)."""
        stmt = (
            select(Product)
            .where(Product.deleted_at.is_(None))
            .order_by(func.lower(Product.name))
        )
        return self._session.scalars(stmt).all()
