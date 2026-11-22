"""Shared fixtures for the tiered limiter tests.

The example tiers come from spec.md "User Scenarios & Testing":
Free = capacity 5, refill 1 token/s; Pro = capacity 20, refill 10 tokens/s;
Layered (AC-009) = limit A (5, 5/s) and limit B (10, 1/6 token/s).

``tiered_limiter`` is imported inside the fixtures, so this file still loads
before the package exists and each test module reports its own import error.
"""

from fractions import Fraction

import pytest


class FakeClock:
    """Injected clock whose reading is set by the test (seconds, exact)."""

    def __init__(self, t: int | Fraction = 0) -> None:
        self.t = t
        self.calls = 0

    def now(self) -> int | Fraction:
        self.calls += 1
        return self.t


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def free():
    from tiered_limiter import Limit, Tier

    return Tier("Free", (Limit(5, 1),))


@pytest.fixture
def pro():
    from tiered_limiter import Limit, Tier

    return Tier("Pro", (Limit(20, 10),))


@pytest.fixture
def layered():
    from tiered_limiter import Limit, Tier

    return Tier("Layered", (Limit(5, 5), Limit(10, Fraction(1, 6))))


@pytest.fixture
def make_limiter(fake_clock):
    """Return a factory: make_limiter(*tiers) -> TieredLimiter on fake_clock."""
    from tiered_limiter import LimiterConfig, TieredLimiter

    def make(*tiers):
        return TieredLimiter(LimiterConfig(tuple(tiers)), fake_clock)

    return make
