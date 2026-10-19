"""Bound consumed API request bytes before body parsers; keep multipart cleanup."""
import asyncio
import math
from starlette.datastructures import Headers
from starlette.formparsers import MultiPartException
from starlette.responses import JSONResponse
from api_security import API_HEADERS

MIB = 1024 * 1024
JSON_BODY_BYTES = 2 * MIB
UPLOAD_BODY_BYTES = {
    "/api/upload": 64 * MIB,
    "/api/documents/upload": 64 * MIB,
    "/api/documents/import-batch": 64 * MIB,
    "/api/documents/link-batch": 2 * MIB,
    "/api/documents/metadata-batch": 3 * MIB,
    "/api/invoices/parse-xml": 6 * MIB,
    "/api/portfolio/import-xlsx": 64 * MIB,
    "/api/portfolio/restore-commissions": 64 * MIB,
    "/api/leads/import": 64 * MIB,
}


class RequestBodyTooLarge(MultiPartException):
    # Starlette closes any partially spooled multipart files on this exception.
    pass


class RequestBodyTimedOut(MultiPartException):
    pass


class RequestBodyLimits:
    def __init__(self, app, allowed_origins=(), json_limit=JSON_BODY_BYTES, upload_limits=None,
                 active_limit=16, idle_read_timeout=30, body_read_timeout=300):
        self.app = app
        self.active_limit = active_limit
        self.active = 0
        self.idle_read_timeout = idle_read_timeout
        self.body_read_timeout = body_read_timeout
        if type(active_limit) is not int or active_limit < 1:
            raise ValueError("Active request limit must be a positive integer")
        if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
               for value in (idle_read_timeout, body_read_timeout)):
            raise ValueError("Body timeouts must be positive finite numbers")
        self.allowed_origins = tuple(allowed_origins)
        self.json_limit = json_limit
        self.upload_limits = dict(UPLOAD_BODY_BYTES if upload_limits is None else upload_limits)
        if any(type(value) is not int or value < 1 for value in [json_limit, *self.upload_limits.values()]):
            raise ValueError("Request body limits must be positive integers")

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        if scope["type"] != "http" or (path != "/api" and not path.startswith("/api/")):
            return await self.app(scope, receive, send)
        limit = self.upload_limits.get(path.rstrip("/"), self.json_limit)
        headers = scope.get("headers", [])
        lengths = [value for name, value in headers if name.lower() == b"content-length"]
        transfer = any(name.lower() == b"transfer-encoding" for name, _ in headers)

        async def reject(status):
            response_headers = dict(API_HEADERS)
            origin = Headers(scope=scope).get("origin")
            if origin in self.allowed_origins:
                response_headers.update({"Access-Control-Allow-Origin": origin, "Vary": "Origin"})
            messages = {400: "Requisição inválida", 413: "Corpo da requisição acima do limite permitido",
                        408: "Tempo limite de recebimento excedido", 503: "Serviço ocupado. Tente novamente."}
            if status == 503: response_headers["Retry-After"] = "1"
            message = messages[status]
            await JSONResponse({"detail": message}, status_code=status, headers=response_headers)(scope, receive, send)

        if lengths:
            if len(lengths) != 1 or transfer or len(lengths[0]) > 20 or not lengths[0] or any(char < 48 or char > 57 for char in lengths[0]):
                return await reject(400)
            if int(lengths[0]) > limit:
                return await reject(413)

        # A synchronous counter has no await between check/increment. Each ASGI
        # worker owns its instance; no event-loop-bound lock survives test loops.
        if self.active >= self.active_limit:
            return await reject(503)
        self.active += 1
        received = 0
        failure_status = None
        started = replaced = body_complete = False
        began = asyncio.get_running_loop().time()

        def abort(status):
            nonlocal failure_status
            failure_status = status
            if status == 408:
                raise RequestBodyTimedOut("Request body read timeout") from None
            raise RequestBodyTooLarge("Request body limit exceeded") from None

        def interruption():
            return "Request body read timeout after response started" if failure_status == 408 else "Request body limit exceeded after response started"

        async def limited_receive():
            nonlocal received, body_complete
            if failure_status is not None: abort(failure_status)
            # Streaming response disconnect listeners must not inherit a timeout
            # once the request body has finished.
            if body_complete: return await receive()
            remaining = self.body_read_timeout - (asyncio.get_running_loop().time() - began)
            if remaining <= 0: abort(408)
            try:
                message = await asyncio.wait_for(receive(), min(self.idle_read_timeout, remaining))
            except asyncio.TimeoutError:
                abort(408)
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Never deliver the offending chunk to the body parser.
                    abort(413)
                body_complete = not message.get("more_body", False)
            elif message["type"] == "http.disconnect":
                body_complete = True
            return message

        async def limited_send(message):
            nonlocal started, replaced
            if failure_status is not None:
                if not started:
                    started = replaced = True
                    await reject(failure_status)
                elif not replaced:
                    raise RuntimeError(interruption()) from None
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            try:
                await self.app(scope, limited_receive, limited_send)
            except Exception:
                if failure_status is None: raise
                if replaced: return
                if started: raise RuntimeError(interruption()) from None
                return await reject(failure_status)
            if failure_status is not None and not replaced:
                if started: raise RuntimeError(interruption()) from None
                await reject(failure_status)
        finally:
            self.active -= 1
