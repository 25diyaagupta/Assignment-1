"""Tiered token-bucket rate limiter with an HTTP 200/429 mapping.

Clients are assigned to named tiers, each with one or more token-bucket limits.
A request is allowed only when every limit of the tier holds its cost. All
arithmetic is exact (``int`` and ``Fraction``), and time comes only from an
injected ``Clock``.

The limiter is not thread-safe: the integrator must serialise access to a
``TieredLimiter`` instance.
"""

from tiered_limiter.clock import Clock, MonotonicClock
from tiered_limiter.config import Limit, LimiterConfig, Tier
from tiered_limiter.errors import CostExceedsCapacityError, UnknownTierError
from tiered_limiter.http_mapping import HttpOutcome, to_http
from tiered_limiter.limiter import Decision, TieredLimiter

__all__: list[str] = [
    "Clock",
    "MonotonicClock",
    "Limit",
    "Tier",
    "LimiterConfig",
    "TieredLimiter",
    "Decision",
    "HttpOutcome",
    "to_http",
    "UnknownTierError",
    "CostExceedsCapacityError",
]
