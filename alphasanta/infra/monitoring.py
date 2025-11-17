"""Minimal health and rate limiting helpers."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass
class HealthStatus:
    processed_tasks: int
    failed_tasks: int
    last_error: Optional[str] = None


class HealthMonitor:
    def __init__(self) -> None:
        self.processed = 0
        self.failed = 0
        self.last_error: Optional[str] = None

    def record_success(self) -> None:
        self.processed += 1

    def record_failure(self, error: Exception) -> None:
        self.failed += 1
        self.last_error = str(error)

    def snapshot(self) -> HealthStatus:
        return HealthStatus(self.processed, self.failed, self.last_error)


class RateLimiter:
    """Simple sliding-window rate limiter."""

    def __init__(self, limit_per_minute: int) -> None:
        self.limit = limit_per_minute
        self.events: Dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        window = self.events[key]
        now = time.time()
        cutoff = now - 60
        while window and window[0] < cutoff:
            window.popleft()
        if len(window) >= self.limit:
            return False
        window.append(now)
        return True
