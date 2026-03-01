from starlette.testclient import TestClient

from src.main import app


class TestRequestIDMiddleware:
    def test_generates_request_id(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health")
        assert "X-Request-ID" in response.headers

    def test_propagates_provided_request_id(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/health", headers={"X-Request-ID": "my-trace-123"})
        assert response.headers["X-Request-ID"] == "my-trace-123"
