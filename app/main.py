from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.stores.router import router as stores_router
from app.requests.router import router as requests_router
from app.forecast.router import router as forecast_router
from app.recommendations.router import router as recommendations_router
from app.products.router import router as products_router

from app.shared.config import get_settings
from app.shared.errors import (
    DomainError,
    DuplicateProductNameError,
    DuplicateStoreNameError,
    EmptyNameError,
    InvalidForecastHorizonError,
    InvalidLeadTimeError,
    InvalidPolicyHorizonError,
    InvalidReceiptQuantityError,
    InvalidReplenishmentWindowError,
    InvalidServiceLevelError,
    ProductDeletionBlockedError,
    ProductNotFoundError,
    StoreNotFoundError,
    RequestNotFoundError,
    RequestAlreadyProcessedError,
    InsufficientStockError,
    InvalidRequestQuantityError,
    StoreDeletionBlockedError,
)


_STATUS_BY_TYPE: dict[type[DomainError], int] = {
    EmptyNameError: 400,
    InvalidReceiptQuantityError: 422,
    DuplicateProductNameError: 409,
    DuplicateStoreNameError: 409,
    ProductDeletionBlockedError: 409,
    ProductNotFoundError: 404,
    StoreNotFoundError: 404,
    RequestNotFoundError: 404,
    RequestAlreadyProcessedError: 409,
    InsufficientStockError: 409,
    InvalidRequestQuantityError: 422,
    StoreDeletionBlockedError: 409,
    InvalidForecastHorizonError: 422,
    InvalidServiceLevelError: 422,
    InvalidLeadTimeError: 422,
    InvalidPolicyHorizonError: 422,
    InvalidReplenishmentWindowError: 422,
}


def _status_for(error: DomainError) -> int:
    for cls in type(error).__mro__:
        if cls in _STATUS_BY_TYPE:
            return _STATUS_BY_TYPE[cls]
    return 400


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # ADR-0009: the whole REST API lives under /api — the root namespace
    # belongs to the SPA routes (one origin in prod, Vite proxy in dev).
    # The loop makes forgetting the prefix impossible for future routers.
    for router in (
        products_router,
        stores_router,
        requests_router,
        forecast_router,
        recommendations_router,
    ):
        app.include_router(router, prefix="/api")

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        """EL-3: each violated rule gets its own message; texts are not normative."""
        return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})

    return app


app = create_app()
