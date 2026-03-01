import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/lots/{lot_id}")
async def lot_websocket(websocket: WebSocket, lot_id: int) -> None:
    """Subscribe to real-time events for a specific lot.

    Events:
        bid_placed — {"type": "bid_placed","lot_id": 1, "bidder": "Alex", "amount": 105}
        time_extended — {"type": "time_extended", "lot_id": 1, "new_end_time": "..."}
        lot_ended   — {"type": "lot_ended", "lot_id": 1, "final_price": 250}

    Send "ping" to keep connection alive, server replies "pong".
    """
    ws_manager = websocket.app.state.ws_manager

    await ws_manager.connect(lot_id, websocket)
    try:
        while True:
            # keep-alive
            data = await websocket.receive_text()
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(lot_id, websocket)
    except Exception:
        logger.exception("Unexpected WS error for lot %d", lot_id)
        ws_manager.disconnect(lot_id, websocket)
