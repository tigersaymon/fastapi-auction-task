from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.orm.exc import StaleDataError

from src.bids.schemas import BidCreateSchema
from src.lots.exceptions import (
    BidTooLowError,
    ConcurrentUpdateError,
    LotEndedError,
    LotNotFoundError,
)
from src.lots.models import LotStatus
from src.lots.schemas import LotCreateSchema
from src.lots.service import AuctionService
from src.ws.manager import ConnectionManager
from tests.conftest import make_lot, make_uow


@pytest.fixture
def mock_ws() -> ConnectionManager:
    manager = ConnectionManager()
    manager.broadcast = AsyncMock()  # type: ignore[method-assign]
    return manager


class TestCreateLot:
    async def test_creates_with_correct_price(self, mock_ws: ConnectionManager) -> None:
        uow = make_uow()
        service = AuctionService(uow, mock_ws)

        end_time = datetime.now(tz=UTC) + timedelta(hours=1)
        lot = await service.create_lot(
            LotCreateSchema(
                title="Watch",
                start_price=Decimal("100.00"),
                end_time=end_time,
            )
        )

        assert lot.start_price == Decimal("100.00")
        assert lot.current_price == Decimal("100.00")
        assert lot.end_time == end_time
        uow.commit.assert_awaited_once()


class TestGetLot:
    async def test_returns_lot(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(lot_id=1)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        result = await service.get_lot(1)

        assert result.id == 1

    async def test_raises_when_not_found(self, mock_ws: ConnectionManager) -> None:
        uow = make_uow(lot=None)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(LotNotFoundError):
            await service.get_lot(999)


class TestGetActiveLots:
    async def test_returns_lots_and_count(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot()
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        lots, total = await service.get_active_lots(offset=0, limit=20)

        assert total == 1
        assert len(lots) == 1

    async def test_empty_list(self, mock_ws: ConnectionManager) -> None:
        uow = make_uow(lot=None)
        service = AuctionService(uow, mock_ws)

        lots, total = await service.get_active_lots(offset=0, limit=20)

        assert total == 0
        assert lots == []


class TestPlaceBid:
    async def test_success(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=100.0)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        bid = await service.place_bid(
            1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
        )

        assert bid.amount == Decimal("150.00")
        assert bid.bidder == "John"
        assert bid.lot_id == 1
        uow.commit.assert_awaited_once()

    async def test_updates_lot_current_price(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=100.0)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        await service.place_bid(
            1, BidCreateSchema(bidder="Jane", amount=Decimal("200.00"))
        )

        assert lot.current_price == Decimal("200.00")

    async def test_broadcasts_bid_placed_event(
        self, mock_ws: ConnectionManager
    ) -> None:
        lot = make_lot(current_price=100.0)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        await service.place_bid(
            1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
        )

        mock_ws.broadcast.assert_any_call(  # type: ignore[union-attr]
            lot_id=1,
            message={
                "type": "bid_placed",
                "lot_id": 1,
                "bidder": "John",
                "amount": Decimal("150.00"),
            },
        )


class TestPlaceBidValidation:
    async def test_lot_not_found(self, mock_ws: ConnectionManager) -> None:
        uow = make_uow(lot=None)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(LotNotFoundError):
            await service.place_bid(
                999, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
            )

    async def test_lot_ended_by_status(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(status=LotStatus.ENDED)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(LotEndedError):
            await service.place_bid(
                1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
            )

    async def test_lot_ended_by_time(self, mock_ws: ConnectionManager) -> None:
        """Ghost bid prevention: status is RUNNING but end_time already passed"""
        lot = make_lot(status=LotStatus.RUNNING, minutes_left=-1)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(LotEndedError):
            await service.place_bid(
                1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
            )

    async def test_bid_too_low(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=200.0)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(BidTooLowError):
            await service.place_bid(
                1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
            )

    async def test_bid_equal_to_current_price(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=100.0)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        with pytest.raises(BidTooLowError):
            await service.place_bid(
                1, BidCreateSchema(bidder="John", amount=Decimal("100.00"))
            )


class TestTimeExtension:
    async def test_extends_when_near_end(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=100.0, minutes_left=2)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        original_end_time = lot.end_time
        await service.place_bid(
            1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
        )

        assert lot.end_time > original_end_time

    async def test_broadcasts_time_extended(self, mock_ws: ConnectionManager) -> None:
        lot = make_lot(current_price=100.0, minutes_left=2)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        await service.place_bid(
            1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
        )

        assert mock_ws.broadcast.await_count == 2

    async def test_no_extension_when_far_from_end(
        self, mock_ws: ConnectionManager
    ) -> None:
        lot = make_lot(current_price=100.0, minutes_left=30)
        uow = make_uow(lot)
        service = AuctionService(uow, mock_ws)

        original_end_time = lot.end_time
        await service.place_bid(
            1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
        )

        assert lot.end_time == original_end_time


class TestConcurrency:
    async def test_stale_data_error_raises_concurrent_update(
        self, mock_ws: ConnectionManager
    ) -> None:
        lot = make_lot(current_price=100.0)
        uow = make_uow(lot)
        uow.commit = AsyncMock(side_effect=StaleDataError("stale"))
        service = AuctionService(uow, mock_ws)

        with pytest.raises(ConcurrentUpdateError):
            await service.place_bid(
                1, BidCreateSchema(bidder="John", amount=Decimal("150.00"))
            )
