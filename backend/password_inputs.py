"""Validate bcrypt input without silently truncating or normalizing passwords."""
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.responses import JSONResponse


def password_bytes(value, minimum=1):
    if not isinstance(value, str) or len(value) < minimum or "\x00" in value:
        raise ValueError("Invalid password length or characters")
    raw = value.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("Password exceeds bcrypt's 72-byte limit")
    return raw


async def auth_validation_error(request, exc):
    if request.url.path.startswith("/api/auth/"):
        # FastAPI's default validation errors include raw submitted inputs.
        # Do not echo passwords or malformed authentication payloads.
        return JSONResponse(status_code=422, content={"detail":"Dados de autenticação inválidos."},
                            headers={"Cache-Control":"no-store"})
    return await request_validation_exception_handler(request, exc)
