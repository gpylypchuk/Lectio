from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.llm import (
    Analyzer,
    AnthropicAnalyzer,
    InvalidLLMOutputError,
    LLMError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.schemas import AnalysisRequest, AnalysisResult

# Long enough for a rate limit or an overload to clear on the provider side (D8).
RETRY_AFTER_SECONDS = 30

# Client-facing status and message per domain error. The details stay in the logs (D8).
ERROR_RESPONSES: dict[type[LLMError], tuple[int, str]] = {
    ProviderUnavailableError: (503, "LLM provider unavailable, try again later."),
    InvalidLLMOutputError: (502, "The LLM did not return a valid summary."),
    ProviderRequestError: (500, "Internal server error."),
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Reading settings here makes a missing API key fail at startup, not on the first request.
    analyzer = AnthropicAnalyzer(get_settings())
    app.state.analyzer = analyzer
    yield
    await analyzer.aclose()


app = FastAPI(title="Lectio", lifespan=lifespan)


def get_analyzer(request: Request) -> Analyzer:
    analyzer: Analyzer = request.app.state.analyzer
    return analyzer


AnalyzerDep = Annotated[Analyzer, Depends(get_analyzer)]


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError) -> JSONResponse:
    status_code, detail = ERROR_RESPONSES.get(type(exc), (500, "Internal server error."))
    headers = (
        {"Retry-After": str(RETRY_AFTER_SECONDS)}
        if isinstance(exc, ProviderUnavailableError)
        else None
    )
    return JSONResponse(status_code=status_code, content={"detail": detail}, headers=headers)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    # Liveness only. Calling the LLM here would let a provider outage restart healthy instances.
    return {"status": "ok"}


@app.post("/v1/analyses")
async def create_analysis(body: AnalysisRequest, analyzer: AnalyzerDep) -> AnalysisResult:
    return await analyzer.analyze(body.text)
