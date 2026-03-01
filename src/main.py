import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.core.config import get_settings
from src.core.exception_handlers import register_exception_handlers
from src.core.logging_config import setup_logging
from src.core.middleware import RequestIDMiddleware
from src.lots.router import router as lots_router
from src.tasks.scheduler import scheduler_loop
from src.ws.manager import ConnectionManager
from src.ws.router import router as ws_router

settings = get_settings()
setup_logging(debug=settings.DEBUG)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ws_manager = ConnectionManager()

    scheduler_task = asyncio.create_task(scheduler_loop(app.state.ws_manager))
    logger.info("Application started")

    yield

    scheduler_task.cancel()

    with suppress(asyncio.CancelledError):
        await scheduler_task

    logger.info("Application stopped")


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(lots_router, prefix=settings.API_PREFIX)
app.include_router(ws_router, prefix=settings.API_PREFIX)

register_exception_handlers(app)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
