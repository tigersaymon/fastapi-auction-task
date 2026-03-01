from unittest.mock import AsyncMock, MagicMock, patch

from src.lots.models import LotStatus
from src.tasks.scheduler import close_expired_lots


class TestCloseExpiredLots:
    async def test_closes_expired_lots(self) -> None:
        lot = MagicMock()
        lot.id = 1
        lot.current_price = 250.0
        lot.status = LotStatus.RUNNING

        mock_uow = AsyncMock()
        mock_uow.lots.get_expired_running = AsyncMock(return_value=[lot])
        mock_uow.commit = AsyncMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_ws = AsyncMock()

        with patch("src.tasks.scheduler.SQLAlchemyUnitOfWork", return_value=mock_uow):
            await close_expired_lots(mock_ws)

        assert lot.status == LotStatus.ENDED
        mock_uow.commit.assert_awaited_once()
        mock_ws.broadcast.assert_awaited_once_with(
            lot_id=1,
            message={
                "type": "lot_ended",
                "lot_id": 1,
                "final_price": 250.0,
            },
        )

    async def test_no_expired_lots_is_noop(self) -> None:
        mock_uow = AsyncMock()
        mock_uow.lots.get_expired_running = AsyncMock(return_value=[])
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_ws = AsyncMock()

        with patch("src.tasks.scheduler.SQLAlchemyUnitOfWork", return_value=mock_uow):
            await close_expired_lots(mock_ws)

        mock_uow.commit.assert_not_awaited()
        mock_ws.broadcast.assert_not_awaited()

    async def test_closes_multiple_lots(self) -> None:
        lots = []
        for i in range(3):
            lot = MagicMock()
            lot.id = i + 1
            lot.current_price = 100.0 * (i + 1)
            lot.status = LotStatus.RUNNING
            lots.append(lot)

        mock_uow = AsyncMock()
        mock_uow.lots.get_expired_running = AsyncMock(return_value=lots)
        mock_uow.commit = AsyncMock()
        mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
        mock_uow.__aexit__ = AsyncMock(return_value=None)

        mock_ws = AsyncMock()

        with patch("src.tasks.scheduler.SQLAlchemyUnitOfWork", return_value=mock_uow):
            await close_expired_lots(mock_ws)

        for lot in lots:
            assert lot.status == LotStatus.ENDED

        assert mock_ws.broadcast.await_count == 3
