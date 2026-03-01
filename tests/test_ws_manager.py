import pytest

from src.ws.manager import ConnectionManager
from tests.conftest import make_ws


@pytest.fixture
def manager() -> ConnectionManager:
    return ConnectionManager()


class TestConnect:
    async def test_adds_subscriber(self, manager: ConnectionManager) -> None:
        ws = make_ws()
        await manager.connect(lot_id=1, websocket=ws)
        assert manager.subscriber_count(1) == 1
        ws.accept.assert_awaited_once()

    async def test_multiple_subscribers(self, manager: ConnectionManager) -> None:
        await manager.connect(1, make_ws())
        await manager.connect(1, make_ws())
        assert manager.subscriber_count(1) == 2

    async def test_different_lots_isolated(self, manager: ConnectionManager) -> None:
        await manager.connect(1, make_ws())
        await manager.connect(2, make_ws())
        assert manager.subscriber_count(1) == 1
        assert manager.subscriber_count(2) == 1


class TestDisconnect:
    async def test_removes_subscriber(self, manager: ConnectionManager) -> None:
        ws = make_ws()
        await manager.connect(1, ws)
        manager.disconnect(1, ws)
        assert manager.subscriber_count(1) == 0

    async def test_cleans_up_empty_channel(self, manager: ConnectionManager) -> None:
        ws = make_ws()
        await manager.connect(1, ws)
        manager.disconnect(1, ws)
        assert 1 not in manager.active_lot_ids()


class TestBroadcast:
    async def test_sends_to_all_subscribers(self, manager: ConnectionManager) -> None:
        ws1, ws2 = make_ws(), make_ws()
        await manager.connect(1, ws1)
        await manager.connect(1, ws2)

        await manager.broadcast(1, {"type": "bid_placed", "amount": 100})

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()

    async def test_ignores_other_lots(self, manager: ConnectionManager) -> None:
        ws1, ws2 = make_ws(), make_ws()
        await manager.connect(1, ws1)
        await manager.connect(2, ws2)

        await manager.broadcast(1, {"type": "bid_placed"})

        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_not_awaited()

    async def test_prunes_dead_connections(self, manager: ConnectionManager) -> None:
        ws_alive = make_ws()
        ws_dead = make_ws()
        ws_dead.send_text.side_effect = RuntimeError("broken pipe")

        await manager.connect(1, ws_alive)
        await manager.connect(1, ws_dead)

        await manager.broadcast(1, {"type": "bid_placed"})

        assert manager.subscriber_count(1) == 1

    async def test_no_subscribers_is_noop(self, manager: ConnectionManager) -> None:
        await manager.broadcast(999, {"type": "bid_placed"})
