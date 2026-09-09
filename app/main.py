from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.products.router import router as products_router
from app.shared.config import get_settings
from app.shared.errors import (
    DomainError,
    DuplicateProductNameError,
    EmptyNameError,
    InvalidReceiptQuantityError,
    ProductDeletionBlockedError,
    ProductNotFoundError,
)

_STATUS_BY_TYPE: dict[type[DomainError], int] = {
    EmptyNameError: 400,
    InvalidReceiptQuantityError: 422,
    DuplicateProductNameError: 409,
    ProductDeletionBlockedError: 409,
    ProductNotFoundError: 404,
}


def _status_for(error: DomainError) -> int:
    for cls in type(error).__mro__:
        if cls in _STATUS_BY_TYPE:
            return _STATUS_BY_TYPE[cls]
    return 400


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.include_router(products_router)

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        """EL-3: each violated rule gets its own message; texts are not normative."""
        return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})

    return app


app = create_app()
