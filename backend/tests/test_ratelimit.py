import pytest

from app.ratelimit import RateLimiter, RateLimitExceededError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


def test_per_client_cap_does_not_affect_other_clients(clock: FakeClock) -> None:
    limiter = RateLimiter(per_client=2, total=10, window_seconds=60, clock=clock)
    limiter.hit("a")
    limiter.hit("a")

    with pytest.raises(RateLimitExceededError):
        limiter.hit("a")
    limiter.hit("b")


def test_total_cap_applies_across_clients(clock: FakeClock) -> None:
    limiter = RateLimiter(per_client=5, total=2, window_seconds=60, clock=clock)
    limiter.hit("a")
    limiter.hit("b")

    with pytest.raises(RateLimitExceededError):
        limiter.hit("c")


def test_window_slides(clock: FakeClock) -> None:
    limiter = RateLimiter(per_client=1, total=10, window_seconds=60, clock=clock)
    limiter.hit("a")

    clock.now = 59.0
    with pytest.raises(RateLimitExceededError) as excinfo:
        limiter.hit("a")
    assert excinfo.value.retry_after_seconds == 1

    clock.now = 60.0
    limiter.hit("a")


def test_rejected_hits_are_not_counted(clock: FakeClock) -> None:
    limiter = RateLimiter(per_client=1, total=10, window_seconds=60, clock=clock)
    limiter.hit("a")
    clock.now = 30.0
    with pytest.raises(RateLimitExceededError):
        limiter.hit("a")

    # Only the hit at 0 counts, so the client is free again at 60 and not at 90.
    clock.now = 60.0
    limiter.hit("a")
