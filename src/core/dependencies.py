from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from src.core.interfaces import AbstractUnitOfWork, SQLAlchemyUnitOfWork
from ws.manager import ConnectionManager


def get_uow() -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork()


def get_ws_manager(conn: HTTPConnection) -> ConnectionManager:
    return conn.app.state.ws_manager


UnitOfWorkDep = Annotated[AbstractUnitOfWork, Depends(get_uow)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_ws_manager)]
