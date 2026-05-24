"""
Request Logging Middleware
Logs every request with unique ID, duration, and status.

At Siemens this data goes to Azure Monitor.
For us it goes to console and can be stored in Supabase.

Correlation IDs are standard practice at enterprise 
companies — every request is traceable end to end.
"""

import logging
import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs every incoming request.
    
    What it captures:
    - Unique request ID (correlation ID)
    - HTTP method and path
    - Status code
    - Duration in milliseconds
    - Client IP address
    
    At Siemens this is mandatory for every service.
    Enables end-to-end request tracing in production.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate unique ID for this request
        # This ID can be used to trace request across
        # all logs, agent calls, and database entries
        request_id = str(uuid.uuid4())[:8]

        # Attach request ID to request state
        # So any agent can reference it in their own logs
        request.state.request_id = request_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        logger.info(
            f"[{request_id}] "
            f"→ {request.method} {request.url.path} "
            f"from {request.client.host}"
        )

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Log completed request with result
        logger.info(
            f"[{request_id}] "
            f"← {request.method} {request.url.path} "
            f"Status: {response.status_code} "
            f"Duration: {duration_ms:.1f}ms"
        )

        # Add request ID to response headers
        # At Siemens this helps frontend engineers
        # report which request failed
        response.headers["X-Request-ID"] = request_id

        return response