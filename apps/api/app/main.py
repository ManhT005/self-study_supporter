import logging
import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import Depends, FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyCookie
from starlette.exceptions import HTTPException

from study_supporter.bootstrap import ApplicationFactory
from study_supporter.config import Settings
from study_supporter.domain.auth import AuthError
from study_supporter.domain.errors import DocumentUnsupported, EvidenceNotFound, QuotaExceeded
from study_supporter.domain.errors import EmbeddingUnavailable
from study_supporter.domain.provider_errors import ProviderAuthenticationError, ProviderUnavailable

from apps.api.app.schemas import Credentials, ErrorDTO, Identity
from apps.api.app.security import AuthLimiter, Sessions

COOKIE = "study_session"
logger = logging.getLogger("study.api")
session_cookie = APIKeyCookie(name=COOKIE, auto_error=False)


@dataclass(frozen=True)
class HTTPSettings:
    origin: str = "http://localhost:3000"
    secure_cookie: bool = True
    session_ttl: int = 8 * 3600

    @classmethod
    def from_env(cls):
        return cls(
            origin=os.getenv("WEB_ORIGIN", "http://localhost:3000"),
            secure_cookie=os.getenv("API_SECURE_COOKIE", "true").lower() != "false",
        )


def principal(request: Request, token: str | None = Depends(session_cookie)):
    user = request.app.state.sessions.get(token)
    if user is None:
        raise HTTPException(401, "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")
    return user


def create_app(factory_builder=None, http_settings=None):
    http = http_settings or HTTPSettings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        from starlette.concurrency import run_in_threadpool

        factory = await run_in_threadpool(
            factory_builder or (lambda: ApplicationFactory(Settings.from_mapping(os.environ)))
        )
        app.state.factory = factory
        try:
            await run_in_threadpool(factory.verify_schema)
            if hasattr(factory.documents, "recover_interrupted"):
                await run_in_threadpool(factory.documents.recover_interrupted)
            yield
        finally:
            await run_in_threadpool(factory.close)

    errors = {
        status: {"model": ErrorDTO} for status in [401, 403, 404, 409, 413, 422, 429, 500, 503]
    }
    app = FastAPI(
        title="Self Study Supporter API", version="1.0.0", lifespan=lifespan, responses=errors
    )
    app.state.sessions = Sessions(ttl=http.session_ttl)
    app.state.limiter = AuthLimiter()

    def error(request, status, code, message):
        return JSONResponse(
            status_code=status,
            content={"code": code, "message": message, "request_id": request.state.request_id},
        )

    @app.middleware("http")
    async def boundary(request, call_next):
        request.state.request_id = uuid.uuid4().hex
        if (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and request.headers.get("origin") != http.origin
        ):
            response = error(request, 403, "origin_denied", "Nguồn yêu cầu không hợp lệ.")
        else:
            try:
                response = await call_next(request)
            except Exception:
                # Do not log exception text: providers may include secrets/prompts.
                logger.error("request_failed request_id=%s", request.state.request_id)
                response = error(
                    request, 500, "internal_error", "Không thể xử lý yêu cầu. Vui lòng thử lại."
                )
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info(
            "request_complete method=%s status=%s request_id=%s",
            request.method,
            response.status_code,
            request.state.request_id,
        )
        return response

    @app.exception_handler(HTTPException)
    async def http_error(request, exc):
        return error(
            request,
            exc.status_code,
            {401: "unauthenticated", 404: "not_found", 429: "rate_limited"}.get(
                exc.status_code, "request_error"
            ),
            str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error(
            request, 422, "invalid_request", "Dữ liệu chưa hợp lệ. Kiểm tra các trường và thử lại."
        )

    async def domain_error(request, exc):
        if isinstance(exc, EvidenceNotFound):
            return error(request, 404, "not_found", "Không tìm thấy tài liệu hoặc nguồn phù hợp.")
        if isinstance(exc, AuthError):
            return error(
                request,
                409,
                "auth_conflict",
                "Không thể tạo tài khoản. Kiểm tra tên đăng nhập và mật khẩu.",
            )
        if isinstance(exc, DocumentUnsupported):
            return error(
                request,
                422,
                "invalid_pdf",
                "PDF không hợp lệ, quá 20 MB hoặc cần OCR. Chọn PDF có văn bản.",
            )
        if isinstance(exc, QuotaExceeded):
            return error(
                request,
                429,
                "provider_quota",
                "Đã hết hạn mức AI. Thử lại sau hoặc chọn model khác.",
            )
        return error(
            request,
            503,
            "provider_unavailable",
            "Dịch vụ xử lý chưa sẵn sàng. Vui lòng thử lại sau.",
        )

    for exception in [
        EvidenceNotFound,
        AuthError,
        DocumentUnsupported,
        QuotaExceeded,
        EmbeddingUnavailable,
        ProviderAuthenticationError,
        ProviderUnavailable,
        OverflowError,
    ]:
        app.add_exception_handler(exception, domain_error)

    @app.get("/health/live", response_model=Identity)
    def live():
        return Identity(username="live")

    @app.get("/health/ready", response_model=Identity)
    def ready(request: Request):
        try:
            request.app.state.factory.verify_schema()
        except Exception:
            raise HTTPException(503, "Cơ sở dữ liệu chưa sẵn sàng.") from None
        return Identity(username="ready")

    def limit(request):
        address = request.client.host if request.client else "unknown"
        if not app.state.limiter.allow(address):
            raise HTTPException(429, "Quá nhiều lần thử. Vui lòng đợi một phút.")

    @app.post("/api/v1/auth/register", response_model=Identity, status_code=201)
    def register(body: Credentials, request: Request):
        limit(request)
        request.app.state.factory.authentication.register(body.username, body.password)
        return Identity(username=body.username)

    @app.post("/api/v1/auth/login", response_model=Identity)
    def login(body: Credentials, request: Request, response: Response):
        limit(request)
        context = request.app.state.factory.authentication.authenticate(
            body.username, body.password
        )
        if context is None:
            raise HTTPException(401, "Tên đăng nhập hoặc mật khẩu chưa đúng.")
        token = app.state.sessions.issue(context, body.username)
        app.state.sessions.revoke(request.cookies.get(COOKIE))
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            secure=http.secure_cookie,
            samesite="lax",
            max_age=http.session_ttl,
            path="/",
        )
        return Identity(username=body.username)

    @app.get("/api/v1/auth/me", response_model=Identity)
    def me(user=Depends(principal)):
        return Identity(username=user.username)

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(request: Request):
        app.state.sessions.revoke(request.cookies.get(COOKIE))
        response = Response(status_code=204)
        response.delete_cookie(
            COOKIE, path="/", secure=http.secure_cookie, httponly=True, samesite="lax"
        )
        return response

    return app


app = create_app()
