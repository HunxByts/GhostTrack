"""FastAPI app factories for separate public and private admin servers.

Admin and public apps use different processes/host ports. Never put admin app
behind the same public reverse-proxy route as the lookup interface.
"""
from __future__ import annotations

import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from ghosttrack.services import LookupError, ip_lookup, my_ip, phone_lookup, username_lookup
from .auth import AdminAuth, SESSION_AGE
from .state import RateLimiter, Store

WEB_ROOT = Path(__file__).resolve().parents[2] / "web"
PUBLIC_TOOLS = frozenset({"ip", "phone", "username"})


class LookupPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=80)
    region: str = Field(default="ID", min_length=2, max_length=2)
    check: bool = True


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    password: str = Field(min_length=1, max_length=256)


class PublicSwitch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool


def create_app(
    interface: Literal["public", "admin"],
    *,
    database: str | None = None,
    secret_dir: str | None = None,
    secure_cookie: bool | None = None,
    public_limit: int = 30,
    login_limit: int = 5,
) -> FastAPI:
    if interface not in ("public", "admin"):
        raise ValueError("Unknown interface")
    store = Store(database or os.getenv("GHOSTTRACK_DB", "/data/ghosttrack.db"))
    admin_auth = None
    if interface == "admin":
        admin_auth = AdminAuth(secret_dir or os.getenv("GHOSTTRACK_SECRET_DIR", "/run/secrets"))
    if secure_cookie is None:
        secure_cookie = os.getenv("GHOSTTRACK_SECURE_COOKIE", "false").lower() == "true"
    public_limiter = RateLimiter(limit=public_limit, window=60)
    admin_limiter = RateLimiter(limit=60, window=60)
    login_limiter = RateLimiter(limit=login_limit, window=15 * 60)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        store.initialize()
        yield

    app = FastAPI(
        title="GhostTrack Public API" if interface == "public" else "GhostTrack Admin API",
        docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan
    )

    def client_ip(request: Request) -> str:
        # Intentionally ignore X-Forwarded-For to prevent spoofing. Run Uvicorn
        # with --no-proxy-headers; configure rate limiting at your reverse proxy.
        return request.client.host if request.client else "unknown"

    def logged_in(request: Request) -> str:
        assert admin_auth is not None
        csrf = admin_auth.parse_session(request.cookies.get("gt_session"))
        if csrf is None:
            raise HTTPException(401, "Admin authentication required")
        return csrf

    def admin_write(request: Request):
        csrf = logged_in(request)
        token = request.headers.get("x-csrf-token", "")
        if not secrets.compare_digest(token, csrf):
            raise HTTPException(403, "Invalid CSRF token")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        # All POST calls need a custom header: browsers cannot submit them via
        # a cross-site HTML form, and CORS is intentionally not enabled.
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            if request.headers.get("x-ghosttrack-ui") != "1":
                response = JSONResponse({"detail": "Missing application request header"}, status_code=403)
            else:
                response = await call_next(request)
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; base-uri 'none'; form-action 'self'; "
            "script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'"
        )
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok", "interface": interface}

    @app.get("/")
    def home():
        return FileResponse(WEB_ROOT / ("admin.html" if interface == "admin" else "public.html"))

    @app.get("/assets/{asset}")
    def static_asset(asset: Literal["style.css", "app.js"]):
        return FileResponse(WEB_ROOT / "static" / asset)

    @app.get("/api/status")
    def status(request: Request):
        if interface == "admin":
            logged_in(request)
            return {"interface": "admin", "public_enabled": store.public_enabled()}
        return {"interface": "public", "public_enabled": store.public_enabled()}

    @app.post("/api/lookup/{tool}")
    async def lookup(tool: str, payload: LookupPayload, request: Request):
        if tool not in PUBLIC_TOOLS and not (interface == "admin" and tool == "my-ip"):
            raise HTTPException(404, "Unknown lookup type")
        if interface == "admin":
            admin_write(request)
            if not admin_limiter.allow(client_ip(request)):
                raise HTTPException(429, "Too many requests. Try again later.")
        else:
            if not store.public_enabled():
                raise HTTPException(503, "Public lookups are disabled")
            if not public_limiter.allow(client_ip(request)):
                raise HTTPException(429, "Rate limit exceeded. Try again later.")

        try:
            if tool == "ip":
                data = await run_in_threadpool(ip_lookup, payload.value)
            elif tool == "phone":
                data = await run_in_threadpool(phone_lookup, payload.value, region=payload.region)
            elif tool == "username":
                data = await run_in_threadpool(username_lookup, payload.value, check=payload.check)
            else:
                data = await run_in_threadpool(my_ip)
        except LookupError as exc:
            store.count(interface, tool, "error")
            # Internal upstream errors should not reveal targets or internal URLs.
            raise HTTPException(400, str(exc)) from None
        except Exception:
            store.count(interface, tool, "error")
            raise HTTPException(502, "Lookup service is temporarily unavailable") from None
        store.count(interface, tool, "success")
        return {"tool": tool, "result": data}

    if interface == "admin":
        assert admin_auth is not None

        @app.post("/api/admin/login")
        def login(payload: LoginPayload, request: Request, response: Response):
            if not login_limiter.allow(client_ip(request)):
                raise HTTPException(429, "Too many login attempts. Try again later.")
            if not admin_auth.authenticate(payload.password):
                raise HTTPException(401, "Invalid credentials")
            cookie, csrf = admin_auth.new_session()
            response.set_cookie(
                "gt_session", cookie, max_age=SESSION_AGE, httponly=True,
                secure=secure_cookie, samesite="strict", path="/"
            )
            return {"authenticated": True, "csrf": csrf}

        @app.get("/api/admin/me")
        def me(request: Request):
            return {"authenticated": True, "csrf": logged_in(request)}

        @app.post("/api/admin/logout")
        def logout(request: Request, response: Response):
            admin_write(request)
            response.delete_cookie("gt_session", path="/", secure=secure_cookie, samesite="strict")
            return {"authenticated": False}

        @app.get("/api/admin/summary")
        def summary(request: Request):
            logged_in(request)
            return {"public_enabled": store.public_enabled(),
                    "counts": store.summary(), "storage": "Aggregate counts only; no query or visitor data"}

        @app.post("/api/admin/public-access")
        def public_access(payload: PublicSwitch, request: Request):
            admin_write(request)
            store.set_public_enabled(payload.enabled)
            return {"public_enabled": store.public_enabled()}

    return app


# The app targets are importable by Uvicorn. The admin target only starts with
# valid secrets; the public app never loads those secrets.
public_app = create_app("public")


def make_admin_app():
    return create_app("admin")
