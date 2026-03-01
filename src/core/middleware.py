import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.core.logging_config import request_id_ctx

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Inject / propagate a correlation ID for every HTTP request.

    * If the caller provides ``X-Request-ID``, it is reused.
    * Otherwise a new UUID-4 is generated.
    * The ID is stored in a ``ContextVar`` so all log lines within the
      request automatically include it (via ``JSONFormatter``).
    * The ID is echoed back in the response header.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = request.headers.get(REQUEST_ID_HEADER, str(uuid.uuid4()))
        request_id_ctx.set(req_id)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        response.headers[REQUEST_ID_HEADER] = req_id

        logger.info(
            "%s %s → %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed_ms,
        )

        return response
