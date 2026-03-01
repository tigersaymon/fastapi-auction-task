from typing import Annotated

from fastapi import Depends
from starlette.requests import HTTPConnection

from src.core.interfaces import AbstractUnitOfWork, SQLAlchemyUnitOfWork
from src.lots.service import AuctionService
from src.ws.manager import ConnectionManager


def get_uow() -> AbstractUnitOfWork:
    return SQLAlchemyUnitOfWork()


def get_ws_manager(conn: HTTPConnection) -> ConnectionManager:
    return conn.app.state.ws_manager


def get_auction_service(
    uow: Annotated[AbstractUnitOfWork, Depends(get_uow)],
    ws_manager: Annotated[ConnectionManager, Depends(get_ws_manager)],
) -> AuctionService:
    return AuctionService(uow=uow, ws_manager=ws_manager)


UnitOfWorkDep = Annotated[AbstractUnitOfWork, Depends(get_uow)]
ConnectionManagerDep = Annotated[ConnectionManager, Depends(get_ws_manager)]
AuctionServiceDep = Annotated[AuctionService, Depends(get_auction_service)]
