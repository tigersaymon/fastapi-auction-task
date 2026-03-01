from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.lots.models import Lot, LotStatus
from src.ws.manager import ConnectionManager


def make_lot(
    lot_id: int = 1,
    *,
    current_price: float = 100.0,
    status: LotStatus = LotStatus.RUNNING,
    minutes_left: int = 10,
) -> MagicMock:
    lot = MagicMock(spec=Lot)
    lot.id = lot_id
    lot.title = f"Lot {lot_id}"
    lot.description = ""
    lot.start_price = Decimal("50.00")
    lot.current_price = Decimal(str(current_price))
    lot.status = status
    lot.end_time = datetime.now(tz=UTC) + timedelta(minutes=minutes_left)
    lot.created_at = datetime.now(tz=UTC) - timedelta(hours=1)
    lot.version = 1
    lot.bids = []
    return lot


def make_uow(lot: MagicMock | None = None) -> AsyncMock:
    """Create a fully-mocked AbstractUnitOfWork."""
    uow = AsyncMock()
    uow.lots = AsyncMock()
    uow.lots.get_by_id = AsyncMock(return_value=lot)
    uow.lots.get_by_id_with_lock = AsyncMock(return_value=lot)
    uow.lots.get_active = AsyncMock(return_value=[lot] if lot else [])
    uow.lots.count_active = AsyncMock(return_value=1 if lot else 0)
    uow.lots.add = AsyncMock(side_effect=_add_entity)
    uow.bids = AsyncMock()
    uow.bids.add = AsyncMock(side_effect=_add_entity)
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


async def _add_entity(entity):  # noqa
    entity.id = 1
    return entity


def make_ws() -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.fixture
def ws_manager() -> ConnectionManager:
    return ConnectionManager()


@pytest.fixture
def mock_ws_manager() -> ConnectionManager:
    manager = ConnectionManager()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    return manager


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from src.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
