from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.stores.router import router as stores_router
from app.requests.router import router as requests_router
from app.forecast.router import router as forecast_router
from app.recommendations.router import router as recommendations_router
from app.products.router import router as products_router
from app.sales.router import router as sales_router

from app.shared.config import get_settings
from app.shared.errors import (
    DomainError, DuplicateProductNameError, DuplicateStoreNameError, EmptyNameError,
    IdempotencyConflictError, InsufficientStockError, InsufficientStoreStockError,
    InvalidForecastHorizonError, InvalidLeadTimeError, InvalidPolicyHorizonError,
    InvalidReceiptQuantityError, InvalidReplenishmentWindowError,
    InvalidRequestQuantityError, InvalidSaleQuantityError, InvalidServiceLevelError,
    ProductDeletionBlockedError, ProductNotFoundError, RequestAlreadyProcessedError,
    RequestNotFoundError, SaleAlreadyReversedError, SaleNotFoundError,
    StoreDeletionBlockedError, StoreNotFoundError,
)


class SPAStaticFiles(StaticFiles):
    """SPA fallback for non-API paths; unknown API paths remain JSON 404s."""

    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code == 404 and not path.startswith("api"):
                return await super().get_response("index.html", scope)
            raise


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
    InsufficientStoreStockError: 409,
    InvalidRequestQuantityError: 422,
    InvalidSaleQuantityError: 422,
    SaleNotFoundError: 404,
    SaleAlreadyReversedError: 409,
    IdempotencyConflictError: 409,
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

    for router in (
        products_router, stores_router, requests_router, sales_router,
        forecast_router, recommendations_router,
    ):
        app.include_router(router, prefix="/api")

    docs_img = Path(__file__).resolve().parents[1] / "docs" / "img"
    if docs_img.is_dir():
        app.mount("/img", StaticFiles(directory=docs_img), name="img")

    spa_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if spa_dir.is_dir():
        app.mount("/", SPAStaticFiles(directory=spa_dir, html=True), name="spa")

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"detail": str(exc)})

    return app


app = create_app()
