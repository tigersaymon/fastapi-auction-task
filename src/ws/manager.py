import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections grouped by ``lot_id``.

    Each lot has its own channel of subscribers.  The service layer calls
    :meth:`broadcast` after persisting a bid, which fans-out the event to
    every WebSocket client watching that lot.

    Dead connections (broken pipe, etc.) are automatically pruned during
    broadcast to avoid accumulating stale references.
    """

    def __init__(self) -> None:
        self._channels: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, lot_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._channels[lot_id].add(websocket)
        logger.info(
            "WS client connected to lot %d (subscribers: %d)",
            lot_id,
            len(self._channels[lot_id]),
        )

    def disconnect(self, lot_id: int, websocket: WebSocket) -> None:
        self._channels[lot_id].discard(websocket)
        if not self._channels[lot_id]:
            del self._channels[lot_id]
        logger.info("WS client disconnected from lot %d", lot_id)

    async def broadcast(self, lot_id: int, message: dict[str, Any]) -> None:
        """Send a JSON payload to every subscriber of *lot_id*."""
        subscribers = self._channels.get(lot_id)
        if not subscribers:
            return

        payload = json.dumps(message, default=str)
        dead: list[WebSocket] = []

        for ws in subscribers:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            subscribers.discard(ws)
            logger.debug("Pruned dead WS connection for lot %d", lot_id)

        if not subscribers:
            del self._channels[lot_id]

    def subscriber_count(self, lot_id: int) -> int:
        return len(self._channels.get(lot_id, set()))

    def active_lot_ids(self) -> list[int]:
        return list(self._channels.keys())
