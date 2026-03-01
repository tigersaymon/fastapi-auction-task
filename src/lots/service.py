import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm.exc import StaleDataError

from src.bids.models import Bid
from src.bids.schemas import BidCreateSchema
from src.core.config import get_settings
from src.core.interfaces import AbstractUnitOfWork
from src.lots.exceptions import (
    BidTooLowError,
    ConcurrentUpdateError,
    LotEndedError,
    LotNotFoundError,
)
from src.lots.models import Lot, LotStatus
from src.lots.schemas import LotCreateSchema
from src.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)
settings = get_settings()


class AuctionService:
    """Unified service for all auction operations"""

    def __init__(self, uow: AbstractUnitOfWork, ws_manager: ConnectionManager) -> None:
        self._uow = uow
        self._ws = ws_manager

    async def create_lot(self, data: LotCreateSchema) -> Lot:
        async with self._uow:
            lot = Lot(
                title=data.title,
                description=data.description,
                start_price=data.start_price,
                current_price=data.start_price,
                end_time=data.end_time,
            )
            lot = await self._uow.lots.add(lot)
            await self._uow.commit()
            return lot

    async def get_lot(self, lot_id: int) -> Lot:
        async with self._uow:
            lot = await self._uow.lots.get_by_id(lot_id)
            if lot is None:
                raise LotNotFoundError(lot_id)
            return lot

    async def get_active_lots(
        self, *, offset: int = 0, limit: int = 20
    ) -> tuple[list[Lot], int]:
        async with self._uow:
            lots = await self._uow.lots.get_active(offset=offset, limit=limit)
            total = await self._uow.lots.count_active()
            return lots, total

    # Main bid logic
    async def place_bid(self, lot_id: int, data: BidCreateSchema) -> Bid:
        time_was_extended = False
        new_end_time: datetime | None = None

        try:
            async with self._uow:
                lot = await self._uow.lots.get_by_id_with_lock(lot_id)

                if lot is None:
                    raise LotNotFoundError(lot_id)
                now = datetime.now(tz=UTC)
                if lot.status == LotStatus.ENDED or lot.end_time <= now:
                    raise LotEndedError(lot_id)
                if data.amount <= lot.current_price:
                    raise BidTooLowError(lot_id, float(lot.current_price), data.amount)

                bid = Bid(lot_id=lot_id, bidder=data.bidder, amount=data.amount)
                bid = await self._uow.bids.add(bid)
                lot.current_price = data.amount

                # Time extension
                remaining = (lot.end_time - now).total_seconds()

                if remaining < settings.bid_extension_threshold_seconds:
                    lot.end_time += timedelta(seconds=settings.bid_extension_seconds)
                    time_was_extended = True
                    new_end_time = lot.end_time
                    logger.info(
                        "Lot %d end_time extended to %s (bid by %s)",
                        lot_id,
                        lot.end_time.isoformat(),
                        data.bidder,
                    )

                await self._uow.commit()

        except StaleDataError as exc:
            logger.warning("Optimistic lock conflict on lot %d: %s", lot_id, exc)
            raise ConcurrentUpdateError(lot_id) from exc

        # Broadcast AFTER commit
        await self._ws.broadcast(
            lot_id=lot_id,
            message={
                "type": "bid_placed",
                "lot_id": lot_id,
                "bidder": data.bidder,
                "amount": data.amount,
            },
        )

        if time_was_extended and new_end_time is not None:
            await self._ws.broadcast(
                lot_id=lot_id,
                message={
                    "type": "time_extended",
                    "lot_id": lot_id,
                    "new_end_time": new_end_time.isoformat(),
                },
            )

        return bid
