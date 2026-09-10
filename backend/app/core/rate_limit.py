"""SlowAPI rate limiter. Single instance shared by main.py (middleware wiring)
and route decorators. The in-memory / Redis bucketing is handled by slowapi
itself; the app's redis_client cache is used for cross-process cooldowns."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)