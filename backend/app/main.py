import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.llm import (
    Analyzer,
    AnthropicAnalyzer,
    InvalidLLMOutputError,
    LLMError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.ratelimit import RateLimiter, RateLimitExceededError, client_ip
from app.schemas import AnalysisRequest, AnalysisResult

logger = logging.getLogger(__name__)

# Long enough for a rate limit or an overload to clear on the provider side.
RETRY_AFTER_SECONDS = 30

# Only the container image has the built frontend here. Locally Vite serves it.
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "static"

# Client-facing status and message per domain error. The details stay in the logs.
ERROR_RESPONSES: dict[type[LLMError], tuple[int, str]] = {
    ProviderUnavailableError: (503, "LLM provider unavailable, try again later."),
    InvalidLLMOutputError: (502, "The LLM did not return a valid summary."),
    ProviderRequestError: (500, "Internal server error."),
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Reading settings here makes a missing API key fail at startup, not on the first request.
    settings = get_settings()
    analyzer = AnthropicAnalyzer(settings)
    app.state.analyzer = analyzer
    app.state.limiter = RateLimiter(
        per_client=settings.rate_limit_per_ip,
        total=settings.rate_limit_total,
        window_seconds=settings.rate_limit_window_seconds,
    )
    yield
    await analyzer.aclose()


app = FastAPI(title="Lectio", lifespan=lifespan)


def get_analyzer(request: Request) -> Analyzer:
    analyzer: Analyzer = request.app.state.analyzer
    return analyzer


AnalyzerDep = Annotated[Analyzer, Depends(get_analyzer)]


def get_limiter(request: Request) -> RateLimiter:
    limiter: RateLimiter = request.app.state.limiter
    return limiter


LimiterDep = Annotated[RateLimiter, Depends(get_limiter)]


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    status_code, detail = ERROR_RESPONSES.get(type(exc), (500, "Internal server error."))
    headers = (
        {"Retry-After": str(RETRY_AFTER_SECONDS)}
        if isinstance(exc, ProviderUnavailableError)
        else None
    )
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


@app.exception_handler(RateLimitExceededError)
async def rate_limit_handler(request: Request, exc: RateLimitExceededError) -> JSONResponse:
    # Shows in Cloud Logging who hits the limit and whether X-Forwarded-For is parsed right.
    logger.warning("Rate limit hit by %s", client_ip(request))
    minutes = math.ceil(exc.retry_after_seconds / 60)
    return JSONResponse(
        status_code=429,
        content={"detail": f"Too many analyses. Try again in {minutes} min."},
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


# Not /healthz: Cloud Run answers it with its own 404 before it reaches the container.
@app.get("/health")
async def health() -> dict[str, str]:
    # Liveness only. Calling the LLM here would let a provider outage restart healthy instances.
    return {"status": "ok"}


@app.post("/v1/analyses")
async def create_analysis(
    body: AnalysisRequest, request: Request, analyzer: AnalyzerDep, limiter: LimiterDep
) -> AnalysisResult:
    # Counted here, after body validation, so a rejected body does not use up the quota.
    limiter.hit(client_ip(request))
    return await analyzer.analyze(body.text)


def mount_frontend(app: FastAPI, directory: Path) -> None:
    # A mount at / matches every path, so it must come after all API routes.
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")


if FRONTEND_DIR.is_dir():
    mount_frontend(app, FRONTEND_DIR)
