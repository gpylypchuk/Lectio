from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm import (
    AnthropicAnalyzer,
    InvalidLLMOutputError,
    ProviderRequestError,
    ProviderUnavailableError,
)
from app.main import app, get_analyzer, get_limiter, mount_frontend
from app.ratelimit import RateLimiter
from app.schemas import AnalysisResult, PaperSummary

PAPER = "Sleep and memory. " * 40
RESULT = AnalysisResult(
    summary=PaperSummary(
        title="Sleep and Memory Consolidation in Adults",
        tldr="Adults who slept after learning remembered more the next day.",
        study_type="empirical",
        key_findings=["Sleep improved recall by 20%", "The effect was larger for word lists"],
        limitations=[],
        confidence="high",
    ),
    model="fake-model",
)


class FakeAnalyzer:
    def __init__(self, outcome: AnalysisResult | Exception) -> None:
        self.outcome = outcome
        self.texts: list[str] = []

    async def analyze(self, text: str) -> AnalysisResult:
        self.texts.append(text)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@pytest.fixture
def client() -> Iterator[TestClient]:
    # No "with" block, so the real lifespan does not run and no API key is needed.
    use_limiter(per_client=100, total=100)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def frontend(tmp_path: Path) -> Iterator[None]:
    (tmp_path / "index.html").write_text("<title>Lectio</title>")
    mount_frontend(app, tmp_path)
    yield
    # The mount is the last route, so popping it restores the app for other tests.
    app.router.routes.pop()


def use_limiter(per_client: int, total: int) -> None:
    limiter = RateLimiter(per_client=per_client, total=total, window_seconds=3600)
    app.dependency_overrides[get_limiter] = lambda: limiter


def use_analyzer(outcome: AnalysisResult | Exception) -> FakeAnalyzer:
    fake = FakeAnalyzer(outcome)
    app.dependency_overrides[get_analyzer] = lambda: fake
    return fake


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_analysis_returns_summary(client: TestClient) -> None:
    fake = use_analyzer(RESULT)

    response = client.post("/v1/analyses", json={"text": PAPER})

    assert response.status_code == 200
    assert response.json() == RESULT.model_dump(mode="json")
    assert fake.texts == [PAPER.strip()]


@pytest.mark.parametrize(
    "body",
    [{}, {"text": "Too short to be a paper."}, {"text": PAPER, "language": "en"}],
    ids=["missing_text", "short_text", "unknown_field"],
)
def test_invalid_body_returns_422(client: TestClient, body: dict[str, Any]) -> None:
    fake = use_analyzer(RESULT)

    response = client.post("/v1/analyses", json=body)

    assert response.status_code == 422
    assert fake.texts == []


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (ProviderUnavailableError("down"), 503),
        (InvalidLLMOutputError("bad output"), 502),
        (ProviderRequestError("bad request"), 500),
    ],
    ids=["unavailable", "invalid_output", "request_error"],
)
def test_llm_errors_map_to_status_codes(
    client: TestClient, error: Exception, status_code: int
) -> None:
    use_analyzer(error)

    response = client.post("/v1/analyses", json={"text": PAPER})

    assert response.status_code == status_code
    assert "detail" in response.json()
    # Internal messages never reach the client.
    assert str(error) not in response.text
    expected_retry_after = "30" if status_code == 503 else None
    assert response.headers.get("Retry-After") == expected_retry_after


def test_lifespan_creates_and_closes_the_analyzer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    # lru_cache may hold settings built by another test or from the real .env.
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert isinstance(app.state.analyzer, AnthropicAnalyzer)
            assert isinstance(app.state.limiter, RateLimiter)
            assert client.get("/health").status_code == 200
        assert app.state.analyzer._client.is_closed()
    finally:
        get_settings.cache_clear()


@pytest.mark.usefixtures("frontend")
def test_frontend_is_served_at_root(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "<title>Lectio</title>" in response.text


@pytest.mark.usefixtures("frontend")
def test_frontend_does_not_shadow_the_api(client: TestClient) -> None:
    use_analyzer(RESULT)

    assert client.get("/health").json() == {"status": "ok"}
    assert client.post("/v1/analyses", json={"text": PAPER}).status_code == 200


def test_rate_limit_returns_429_with_retry_after(client: TestClient) -> None:
    fake = use_analyzer(RESULT)
    use_limiter(per_client=2, total=10)

    statuses = [client.post("/v1/analyses", json={"text": PAPER}).status_code for _ in range(2)]
    response = client.post("/v1/analyses", json={"text": PAPER})

    assert statuses == [200, 200]
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "3600"
    assert response.json() == {"detail": "Too many analyses. Try again in 60 min."}
    assert len(fake.texts) == 2


def test_rejected_body_does_not_use_quota(client: TestClient) -> None:
    use_analyzer(RESULT)
    use_limiter(per_client=1, total=10)

    assert client.post("/v1/analyses", json={"text": "Too short."}).status_code == 422
    assert client.post("/v1/analyses", json={"text": PAPER}).status_code == 200


def test_rate_limit_keys_on_last_forwarded_address(client: TestClient) -> None:
    use_analyzer(RESULT)
    use_limiter(per_client=1, total=10)

    def post(forwarded_for: str) -> int:
        headers = {"X-Forwarded-For": forwarded_for}
        return client.post("/v1/analyses", json={"text": PAPER}, headers=headers).status_code

    assert post("1.1.1.1, 9.9.9.9") == 200
    # A forged entry on the left does not make the same client look new.
    assert post("2.2.2.2, 9.9.9.9") == 429
    assert post("2.2.2.2, 8.8.8.8") == 200
