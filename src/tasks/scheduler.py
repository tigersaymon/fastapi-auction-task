import asyncio
import logging

from src.core.config import get_settings
from src.core.interfaces import SQLAlchemyUnitOfWork
from src.lots.models import LotStatus
from src.ws.manager import ConnectionManager

logger = logging.getLogger(__name__)
settings = get_settings()


async def close_expired_lots(ws_manager: ConnectionManager) -> None:
    """Find all lots past their end_time and transition them to 'ENDED'.

    Uses ``SELECT … FOR UPDATE SKIP LOCKED`` so multiple workers
    don't fight over the same rows.
    """
    uow = SQLAlchemyUnitOfWork()
    async with uow:
        expired = await uow.lots.get_expired_running()
        if not expired:
            return

        for lot in expired:
            lot.status = LotStatus.ENDED
            logger.info("Lot %d ended at price %.2f", lot.id, lot.current_price)

        await uow.commit()

    for lot in expired:
        await ws_manager.broadcast(
            lot_id=lot.id,
            message={
                "type": "lot_ended",
                "lot_id": lot.id,
                "final_price": lot.current_price,
            },
        )


async def scheduler_loop(ws_manager: ConnectionManager) -> None:
    """Periodically checks for expired lots and closes them.

    Runs as a background ``asyncio.Task`` created during app lifespan.
    """
    logger.info(
        "Lot scheduler started (poll interval: %ds)", settings.scheduler_poll_seconds
    )
    while True:
        try:
            await close_expired_lots(ws_manager)
        except asyncio.CancelledError:
            logger.info("Lot scheduler cancelled")
            raise
        except Exception:
            logger.exception("Scheduler error")
        await asyncio.sleep(settings.scheduler_poll_seconds)
