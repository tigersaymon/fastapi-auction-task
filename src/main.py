from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from core.config import get_settings
from src.lots.router import router as lots_router
from src.ws.manager import ConnectionManager

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ws_manager = ConnectionManager()
    yield


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix=settings.API_PREFIX)

api_router.include_router(lots_router)
