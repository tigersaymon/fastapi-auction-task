from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from src.bids.repository import BidRepository
from src.core.database import async_session_factory
from src.lots.repository import LotRepository

if TYPE_CHECKING:
    from types import TracebackType

    from sqlalchemy.ext.asyncio import AsyncSession

    from src.bids.models import Bid
    from src.core.interfaces import AbstractRepository
    from src.lots.models import Lot


class AbstractUnitOfWork(ABC):
    """Contract guaranteeing transactional consistency across repositories.

    Usage::

        async with uow:
            lot = await uow.lots.get_by_id_with_lock(lot_id)
            await uow.bids.add(bid)
            await uow.commit()
    """

    lots: AbstractRepository[Lot]
    bids: AbstractRepository[Bid]

    @abstractmethod
    async def __aenter__(self) -> AbstractUnitOfWork: ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...


class SQLAlchemyUnitOfWork(AbstractUnitOfWork):
    """Production Unit of Work backed by an async SQLAlchemy session.

    On ``__aenter__`` a new session is created together with fresh
    repository instances that share the same session (and thus the
    same DB transaction).  ``commit`` / ``rollback`` propagate to all
    repositories at once
    """

    def __init__(self) -> None:
        self._session_factory = async_session_factory

    async def __aenter__(self) -> SQLAlchemyUnitOfWork:
        self._session: AsyncSession = self._session_factory()
        self.lots = LotRepository(self._session)
        self.bids = BidRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self._session.close()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
