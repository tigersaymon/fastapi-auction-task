from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base


class AbstractRepository[ModelT: Base](ABC):
    """Contract for every repository"""

    @abstractmethod
    async def get_by_id(self, entity_id: int) -> ModelT | None: ...

    @abstractmethod
    async def get_by_id_with_lock(self, entity_id: int) -> ModelT | None:
        """SELECT … FOR UPDATE"""
        ...

    @abstractmethod
    async def get_all(self, **filters: Any) -> list[ModelT]: ...

    @abstractmethod
    async def add(self, entity: ModelT) -> ModelT: ...


class SQLAlchemyRepository[ModelT: Base](AbstractRepository[ModelT]):
    """Generic SQLAlchemy 2.0 implementation of the repository pattern.

    Subclasses only need to set the ``model`` class attribute.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _base_query(self) -> Select[tuple[ModelT]]:
        return select(self.model)

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        return await self._session.get(self.model, entity_id)

    async def get_by_id_with_lock(self, entity_id: int) -> ModelT | None:
        """Acquire FOR UPDATE lock — prevents concurrent modifications."""
        stmt = self._base_query().where(self.model.id == entity_id).with_for_update()
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, **filters: Any) -> list[ModelT]:
        stmt = self._base_query().filter_by(**filters)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def add(self, entity: ModelT) -> ModelT:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self._session.execute(stmt)
        return result.scalar_one()
