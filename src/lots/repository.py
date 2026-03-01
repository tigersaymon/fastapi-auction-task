from datetime import UTC, datetime

from sqlalchemy import Select, func, select

from src.core.interfaces import SQLAlchemyRepository
from src.lots.models import Lot, LotStatus


class LotRepository(SQLAlchemyRepository[Lot]):
    model = Lot

    async def get_active(self, *, offset: int = 0, limit: int = 20) -> list[Lot]:
        stmt = (
            self._base_query()
            .where(Lot.status == LotStatus.RUNNING)
            .order_by(Lot.end_time.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_active(self) -> int:
        stmt = (
            select(func.count()).select_from(Lot).where(Lot.status == LotStatus.RUNNING)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def get_expired_running(self) -> list[Lot]:
        """Find lots whose end_time has passed but status is still 'RUNNING'"""
        now = datetime.now(tz=UTC)
        stmt: Select[tuple[Lot]] = (
            self._base_query()
            .where(Lot.status == LotStatus.RUNNING, Lot.end_time <= now)
            .with_for_update(skip_locked=True)  # isolation
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
