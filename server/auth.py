from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests without a valid Bearer token.

    The token is read from the API_TOKEN environment variable.
    The /health endpoint is exempt so load-balancers can probe.
    """

    EXEMPT_PATHS = frozenset({"/health"})

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        expected = os.getenv("API_TOKEN", "")
        if not expected:
            return JSONResponse(
                {"error": "Server misconfigured: API_TOKEN not set"},
                status_code=500,
            )

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "Missing Bearer token"}, status_code=401)

        token = auth_header[7:]
        if token != expected:
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        return await call_next(request)
