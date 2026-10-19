"""Public API failures must not disclose upstream payloads or credentials."""
import logging
import uuid
from api_security import API_HEADERS
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

log = logging.getLogger(__name__)


def failure_response(status_code):
    incident = uuid.uuid4().hex
    # Never log exception text, request URL/body, headers or provider payloads.
    log.error("API failure status=%s incident=%s", status_code, incident)
    return JSONResponse(status_code=status_code,
                        content={"detail": "Serviço temporariamente indisponível. Tente novamente.",
                                 "incident_id": incident},
                        headers=API_HEADERS)


async def safe_http_error(request, exc):
    if exc.status_code >= 500:
        return failure_response(exc.status_code)
    # Preserve validation messages and auth/limiter headers such as Retry-After.
    return await http_exception_handler(request, exc)


async def safe_unhandled_error(request, exc):
    return failure_response(500)


def install_error_handlers(app):
    app.add_exception_handler(HTTPException, safe_http_error)
    app.add_exception_handler(Exception, safe_unhandled_error)
