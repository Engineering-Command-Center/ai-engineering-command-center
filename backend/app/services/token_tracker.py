import asyncio
from datetime import UTC, datetime


class TokenTracker:
    """
    In-memory Gemini token usage tracker. Singleton — injected via dependency.
    Resets on process restart; good enough for a dashboard indicator.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._prompt_tokens: int = 0
        self._completion_tokens: int = 0
        self._requests: int = 0
        self._started_at: datetime = datetime.now(UTC)

    async def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        async with self._lock:
            self._prompt_tokens += prompt_tokens
            self._completion_tokens += completion_tokens
            self._requests += 1

    def stats(self) -> dict[str, int | str]:
        return {
            "requests": self._requests,
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
            "since": self._started_at.isoformat(),
        }


# Process-level singleton
_tracker = TokenTracker()


def get_token_tracker() -> TokenTracker:
    return _tracker
