from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import get_settings
from core.exception_handlers import register_exception_handlers
from src.lots.router import router as lots_router
from src.ws.manager import ConnectionManager
from src.ws.router import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ws_manager = ConnectionManager()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(lots_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix=settings.API_PREFIX)
register_exception_handlers(app)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
