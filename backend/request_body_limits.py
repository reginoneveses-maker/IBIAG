"""Bound consumed API request bytes before body parsers; keep multipart cleanup."""
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


class RequestBodyLimits:
    def __init__(self, app, allowed_origins=(), json_limit=JSON_BODY_BYTES, upload_limits=None):
        self.app = app
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
            message = "Corpo da requisição acima do limite permitido" if status == 413 else "Requisição inválida"
            await JSONResponse({"detail": message}, status_code=status, headers=response_headers)(scope, receive, send)

        if lengths:
            if len(lengths) != 1 or transfer or len(lengths[0]) > 20 or not lengths[0] or any(char < 48 or char > 57 for char in lengths[0]):
                return await reject(400)
            if int(lengths[0]) > limit:
                return await reject(413)

        received = 0
        exceeded = started = replaced = False

        async def limited_receive():
            nonlocal received, exceeded
            if exceeded:
                raise RequestBodyTooLarge("Request body limit exceeded")
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    # Never deliver the offending chunk to the body parser.
                    raise RequestBodyTooLarge("Request body limit exceeded")
            return message

        async def limited_send(message):
            nonlocal started, replaced
            if exceeded:
                if not started:
                    started = replaced = True
                    await reject(413)
                elif not replaced:
                    raise RuntimeError("Request body limit exceeded after response started") from None
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, limited_send)
        except Exception:
            if not exceeded:
                raise
            if replaced:
                return
            if started:
                raise RuntimeError("Request body limit exceeded after response started") from None
            return await reject(413)
        if exceeded and not replaced:
            if started:
                raise RuntimeError("Request body limit exceeded after response started") from None
            await reject(413)
