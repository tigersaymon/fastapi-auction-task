from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.ws.manager import ConnectionManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ws_manager = ConnectionManager()
    yield


app = FastAPI(lifespan=lifespan)
