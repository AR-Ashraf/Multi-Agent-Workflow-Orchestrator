"""Cost & safety guardrails (CLAUDE.md §8) — Redis-backed.

Two independent controls, both fail-open-to-*demo* (never to a paid run):

  * **Per-IP rate limit** (§8.2) — a fixed window counter caps how many runs an
    IP may start; over the limit, the request is refused *gracefully* and the
    visitor gets the free cached replay instead of a backend run.
  * **Daily global spend cap** (§8.1) — a per-UTC-day USD counter. It only ever
    gates *house-funded* runs (no-key visitors running on our key, which is OFF
    by default — pure BYOK keeps the floor at $0). A run reserves an estimate
    up-front, then settles to actual cost on completion so the counter stays
    honest. BYOK runs are billed to the visitor and never touch this counter.

Per-run token/step ceilings (§8.3) live in the orchestrator's RunContext; the
gateway just feeds them from settings.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from .config import Settings


def _ip_key(ip: str, bucket: int) -> str:
    return f"cadenza:rl:{ip}:{bucket}"


def _spend_key(day: str) -> str:
    return f"cadenza:spend:{day}"


class Limiter:
    """Wraps an async Redis client with the rate-limit + spend-cap operations."""

    def __init__(self, redis: Any, settings: Settings) -> None:
        self._r = redis
        self._s = settings

    # -- per-IP rate limit --------------------------------------------------
    async def allow_ip(self, ip: str) -> bool:
        """Count one attempt for `ip`; return False once over the window limit."""
        limit = self._s.rate_limit_max_runs
        if limit <= 0:  # 0 / negative disables the limiter
            return True
        window = max(1, self._s.rate_limit_window_seconds)
        bucket = int(time.time()) // window
        key = _ip_key(ip, bucket)
        count = await self._r.incr(key)
        if count == 1:
            await self._r.expire(key, window)
        return count <= limit

    # -- daily global spend cap --------------------------------------------
    @staticmethod
    def _today() -> str:
        return datetime.now(UTC).date().isoformat()

    async def daily_spend(self) -> float:
        raw = await self._r.get(_spend_key(self._today()))
        return float(raw) if raw else 0.0

    async def reserve_house_budget(self, estimate: float) -> bool:
        """Reserve `estimate` USD against today's cap for a house-funded run.

        Returns False (→ caller falls back to demo) when house funding is off or
        the reservation would breach the daily cap.
        """
        if not self._s.house_api_key:
            return False
        if await self.daily_spend() + estimate > self._s.daily_spend_cap_usd:
            return False
        key = _spend_key(self._today())
        await self._r.incrbyfloat(key, estimate)
        await self._r.expire(key, 60 * 60 * 48)  # outlive the day for late settles
        return True

    async def settle_house_spend(self, reserved: float, actual: float) -> None:
        """Reconcile a completed house run's reservation to its actual cost."""
        delta = round(actual - reserved, 6)
        if delta:
            await self._r.incrbyfloat(_spend_key(self._today()), delta)
