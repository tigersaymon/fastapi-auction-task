from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.lots.exceptions import (
    BidTooLowError,
    ConcurrentUpdateError,
    DomainError,
    LotEndedError,
    LotNotFoundError,
)

_STATUS_MAP: dict[type[DomainError], int] = {
    LotNotFoundError: status.HTTP_404_NOT_FOUND,
    LotEndedError: status.HTTP_409_CONFLICT,
    BidTooLowError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ConcurrentUpdateError: status.HTTP_409_CONFLICT,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Map every ``DomainError`` subclass to an appropriate HTTP response."""

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        http_status = _STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        return JSONResponse(
            status_code=http_status,
            content={"detail": exc.detail, "code": exc.code},
        )
