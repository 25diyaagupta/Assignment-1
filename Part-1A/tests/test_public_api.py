"""Public API surface of tiered_limiter (AC-033, constitution XIV)."""

import pytest

import tiered_limiter

# plan.md §Public API (contracts/public-api.md lists the same set).
PUBLIC_NAMES = {
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
}


@pytest.mark.ac("AC-033")
def test_ac033_all_is_exactly_the_eleven_public_names():
    exported = tiered_limiter.__all__
    assert set(exported) == PUBLIC_NAMES
    assert len(exported) == 11
    missing = [name for name in exported if not hasattr(tiered_limiter, name)]
    assert missing == []
