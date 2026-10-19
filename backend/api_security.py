"""Fail-closed API configuration and browser response policy."""
import ipaddress
from urllib.parse import urlsplit
from starlette.datastructures import MutableHeaders, Headers

BASE_HEADERS = {"X-Content-Type-Options":"nosniff", "X-Frame-Options":"DENY",
                "Referrer-Policy":"no-referrer",
                "Permissions-Policy":"camera=(), microphone=(), geolocation=()"}
API_HEADERS = {**BASE_HEADERS, "Cache-Control":"no-store",
               "Content-Security-Policy":"default-src 'none'; frame-ancestors 'none'; base-uri 'none'"}


def cors_origins_from(environ):
    values=environ.get("CORS_ORIGINS","")
    if not values.strip(): return ["http://localhost:3000","http://localhost"]
    origins=[]
    try:
        for value in values.split(","):
            value=value.strip()
            if not value: continue
            if "*" in value or any(ord(char)<32 for char in value): raise ValueError()
            parsed=urlsplit(value)
            if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
                raise ValueError()
            if parsed.path not in {"","/"} or parsed.query or parsed.fragment: raise ValueError()
            host=parsed.hostname.encode("idna").decode().lower()
            if parsed.scheme=="http" and host!="localhost":
                try: loopback=ipaddress.ip_address(host).is_loopback
                except ValueError: loopback=False
                if not loopback: raise ValueError()
            port=parsed.port
            authority="["+host+"]" if ":" in host else host
            if port is not None and port!={"http":80,"https":443}[parsed.scheme]: authority+=":"+str(port)
            origins.append(parsed.scheme+"://"+authority)
    except (ValueError,UnicodeError):
        raise ValueError("CORS_ORIGINS must contain exact HTTPS origins (HTTP only for loopback)") from None
    return list(dict.fromkeys(origins))


def validate_jwt_secret(secret):
    if len(secret)<32 or secret!=secret.strip():
        raise ValueError("JWT_SECRET must contain at least 32 characters without surrounding whitespace")
    return secret


def documentation_options(environ):
    enabled=environ.get("ENABLE_API_DOCS","false").strip().lower()=="true"
    return {"debug":False,"docs_url":"/docs" if enabled else None,
            "redoc_url":"/redoc" if enabled else None,"openapi_url":"/openapi.json" if enabled else None}


class SecurityResponseMiddleware:
    def __init__(self,app,error_response,allowed_origins=()):
        self.app,self.error_response=app,error_response
        self.allowed_origins=tuple(allowed_origins)
    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":
            return await self.app(scope,receive,send)
        started=False
        async def secure_send(message):
            nonlocal started
            if message["type"]=="http.response.start":
                started=True
                headers=MutableHeaders(scope=message)
                for key,value in (API_HEADERS if scope.get("path","").startswith("/api") else BASE_HEADERS).items():
                    if key not in headers: headers[key]=value
            await send(message)
        try:
            await self.app(scope,receive,secure_send)
        except Exception:
            if not started:
                # Reuse the existing redacted incident response. Do not let the
                # server log the original provider exception or request payload.
                response=self.error_response(500)
                origin=Headers(scope=scope).get("origin")
                if origin in self.allowed_origins:
                    response.headers["Access-Control-Allow-Origin"]=origin
                    response.headers["Vary"]="Origin"
                await response(scope,receive,secure_send)
                return
            raise RuntimeError("Response stream interrupted") from None
