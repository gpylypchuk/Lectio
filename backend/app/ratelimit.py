import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request


class RateLimitExceededError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds} s")
        self.retry_after_seconds = retry_after_seconds


class RateLimiter:
    """Sliding window with a cap per client and a cap for everyone.

    State lives in memory, so the caps only hold while the service runs a single instance.
    """

    def __init__(
        self,
        per_client: int,
        total: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._per_client = per_client
        self._total = total
        self._window = window_seconds
        self._clock = clock
        # One entry per accepted request, so memory is bounded by total, not by distinct clients.
        self._hits: deque[tuple[float, str]] = deque()

    def hit(self, client: str) -> None:
        now = self._clock()
        while self._hits and now - self._hits[0][0] >= self._window:
            self._hits.popleft()

        client_hits = [at for at, key in self._hits if key == client]
        if len(client_hits) >= self._per_client:
            raise RateLimitExceededError(self._seconds_until_free(client_hits[0], now))
        if len(self._hits) >= self._total:
            raise RateLimitExceededError(self._seconds_until_free(self._hits[0][0], now))
        self._hits.append((now, client))

    def _seconds_until_free(self, oldest: float, now: float) -> int:
        return max(1, math.ceil(oldest + self._window - now))


def client_ip(request: Request) -> str:
    # Google's front end appends the address it saw, so the last entry is the one a client
    # cannot forge. Anything before it may come from the client.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"
