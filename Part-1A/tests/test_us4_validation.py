"""User Story 4 and addendum: reject invalid input early.

Covers AC-018 to AC-024, AC-028 to AC-031, AC-035 and AC-036.
Source: spec.md, contracts/public-api.md section Errors, and data-model.md.
Every error message starts with the field name and a colon. Wrong types raise
TypeError; wrong values raise ValueError; cost above capacity raises
CostExceedsCapacityError. A rejected acquire leaves every balance untouched.
"""

import re
from fractions import Fraction

import pytest

from tiered_limiter import (
    CostExceedsCapacityError,
    Limit,
    LimiterConfig,
    Tier,
)


def _spent_free_limiter(fake_clock, free, make_limiter):
    """Return a Free limiter where client "alice" has spent 2 of 5 tokens at t=0."""
    limiter = make_limiter(free)
    fake_clock.t = 0
    assert limiter.acquire("alice", "Free", 2).allowed is True
    assert limiter.inspect("alice", "Free") == (3,)
    return limiter


@pytest.mark.ac("AC-018")
@pytest.mark.parametrize("capacity", [0, -1, -5])
def test_ac018_non_positive_capacity_is_rejected(capacity) -> None:
    with pytest.raises(ValueError) as excinfo:
        Limit(capacity, 1)

    assert type(excinfo.value) is ValueError
    assert str(excinfo.value).startswith("capacity:")


@pytest.mark.ac("AC-019")
@pytest.mark.parametrize("rate", [0, -1, Fraction(0), Fraction(-1, 6)])
def test_ac019_non_positive_refill_rate_is_rejected(rate) -> None:
    with pytest.raises(ValueError) as excinfo:
        Limit(5, rate)

    assert type(excinfo.value) is ValueError
    assert str(excinfo.value).startswith("refill_rate:")


@pytest.mark.ac("AC-020")
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("field", ["capacity", "refill_rate"])
def test_ac020_non_finite_capacity_or_rate_is_type_error(field, value) -> None:
    kwargs = {"capacity": 5, "refill_rate": 1, field: value}

    with pytest.raises(TypeError) as excinfo:
        Limit(**kwargs)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith(f"{field}:")


@pytest.mark.ac("AC-021")
def test_ac021_tier_with_no_limits_is_rejected() -> None:
    with pytest.raises(ValueError) as excinfo:
        Tier("Empty", ())

    assert type(excinfo.value) is ValueError
    assert str(excinfo.value).startswith("limits:")


@pytest.mark.ac("AC-022")
@pytest.mark.parametrize(
    "names",
    [("Gold", "Gold"), ("Free", "Gold", "Gold"), ("Gold", "Free", "Gold")],
)
def test_ac022_duplicate_tier_names_are_rejected(names) -> None:
    tiers = tuple(Tier(name, (Limit(5, 1),)) for name in names)

    with pytest.raises(ValueError) as excinfo:
        LimiterConfig(tiers)

    assert type(excinfo.value) is ValueError
    message = str(excinfo.value)
    assert message.startswith("tiers:")
    assert "Gold" in message


@pytest.mark.ac("AC-023")
@pytest.mark.parametrize("cost", [0, -1, -5])
def test_ac023_non_positive_cost_is_rejected_without_taking_tokens(
    fake_clock, free, make_limiter, cost
) -> None:
    limiter = _spent_free_limiter(fake_clock, free, make_limiter)

    with pytest.raises(ValueError) as excinfo:
        limiter.acquire("alice", "Free", cost)

    assert type(excinfo.value) is ValueError
    assert str(excinfo.value).startswith("cost:")
    assert limiter.inspect("alice", "Free") == (3,)


@pytest.mark.ac("AC-023")
@pytest.mark.parametrize("cost", [Fraction(3, 2), Fraction(1, 2), 1.5, 0.5])
def test_ac023_non_whole_cost_is_rejected_without_taking_tokens(
    fake_clock, free, make_limiter, cost
) -> None:
    limiter = _spent_free_limiter(fake_clock, free, make_limiter)

    with pytest.raises(TypeError) as excinfo:
        limiter.acquire("alice", "Free", cost)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("cost:")
    assert limiter.inspect("alice", "Free") == (3,)


@pytest.mark.ac("AC-024")
@pytest.mark.parametrize(
    ("tier_fixture", "tier_name", "cost", "capacity"),
    [
        ("free", "Free", 6, 5),
        ("free", "Free", 100, 5),
        ("pro", "Pro", 21, 20),
        ("layered", "Layered", 6, 5),
    ],
)
def test_ac024_cost_above_capacity_raises_and_takes_nothing(
    request, fake_clock, make_limiter, tier_fixture, tier_name, cost, capacity
) -> None:
    tier = request.getfixturevalue(tier_fixture)
    limiter = make_limiter(tier)
    fake_clock.t = 0
    before = limiter.inspect("alice", tier_name)

    with pytest.raises(CostExceedsCapacityError) as excinfo:
        limiter.acquire("alice", tier_name, cost)

    message = str(excinfo.value)
    assert message.startswith("cost:")
    assert re.search(rf"\b{cost}\b", message) is not None
    assert re.search(rf"\b{capacity}\b", message) is not None
    assert limiter.inspect("alice", tier_name) == before
    assert limiter.acquire("alice", tier_name, capacity).allowed is True


@pytest.mark.ac("AC-028", "AC-029")
@pytest.mark.parametrize("value", [True, False, "5", "", None])
def test_ac028_ac029_bad_type_capacity_is_type_error(value) -> None:
    with pytest.raises(TypeError) as excinfo:
        Limit(value, 1)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("capacity:")


@pytest.mark.ac("AC-028", "AC-029")
@pytest.mark.parametrize("value", [True, False, "1", "", None])
def test_ac028_ac029_bad_type_refill_rate_is_type_error(value) -> None:
    with pytest.raises(TypeError) as excinfo:
        Limit(5, value)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("refill_rate:")


@pytest.mark.ac("AC-028", "AC-029")
@pytest.mark.parametrize("cost", [True, False, "1", "", None])
def test_ac028_ac029_bad_type_cost_is_type_error_and_takes_nothing(
    fake_clock, free, make_limiter, cost
) -> None:
    limiter = _spent_free_limiter(fake_clock, free, make_limiter)

    with pytest.raises(TypeError) as excinfo:
        limiter.acquire("alice", "Free", cost)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("cost:")
    assert limiter.inspect("alice", "Free") == (3,)


@pytest.mark.ac("AC-030")
@pytest.mark.parametrize("capacity", [Fraction(5, 2), 2.5, Fraction(5), 5.0])
def test_ac030_non_int_capacity_is_type_error(capacity) -> None:
    with pytest.raises(TypeError) as excinfo:
        Limit(capacity, 1)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("capacity:")


@pytest.mark.ac("AC-030")
@pytest.mark.parametrize("cost", [2.0, 1.0])
def test_ac030_whole_float_cost_is_type_error_and_takes_nothing(
    fake_clock, free, make_limiter, cost
) -> None:
    limiter = _spent_free_limiter(fake_clock, free, make_limiter)

    with pytest.raises(TypeError) as excinfo:
        limiter.acquire("alice", "Free", cost)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("cost:")
    assert limiter.inspect("alice", "Free") == (3,)


@pytest.mark.ac("AC-031")
@pytest.mark.parametrize(
    ("client_key", "tier_name", "exc_type", "field"),
    [
        ("", "Free", ValueError, "client_key:"),
        (None, "Free", TypeError, "client_key:"),
        (7, "Free", TypeError, "client_key:"),
        (b"alice", "Free", TypeError, "client_key:"),
        ("alice", "", ValueError, "tier_name:"),
        ("alice", None, TypeError, "tier_name:"),
        ("alice", 1, TypeError, "tier_name:"),
        ("alice", b"Free", TypeError, "tier_name:"),
    ],
)
def test_ac031_bad_client_key_or_tier_name_is_rejected_and_takes_nothing(
    fake_clock, free, make_limiter, client_key, tier_name, exc_type, field
) -> None:
    limiter = _spent_free_limiter(fake_clock, free, make_limiter)

    with pytest.raises(exc_type) as excinfo:
        limiter.acquire(client_key, tier_name)

    assert type(excinfo.value) is exc_type
    assert str(excinfo.value).startswith(field)
    assert limiter.inspect("alice", "Free") == (3,)


@pytest.mark.ac("AC-031")
@pytest.mark.parametrize(
    ("name", "exc_type"),
    [("", ValueError), (None, TypeError), (5, TypeError), (b"Free", TypeError)],
)
def test_ac031_bad_tier_name_in_config_is_rejected(name, exc_type) -> None:
    with pytest.raises(exc_type) as excinfo:
        Tier(name, (Limit(5, 1),))

    assert type(excinfo.value) is exc_type
    assert str(excinfo.value).startswith("name:")


@pytest.mark.ac("AC-035")
def test_ac035_empty_tier_list_is_rejected() -> None:
    with pytest.raises(ValueError) as excinfo:
        LimiterConfig(())

    assert type(excinfo.value) is ValueError
    assert str(excinfo.value).startswith("tiers:")


@pytest.mark.ac("AC-036")
@pytest.mark.parametrize(
    "limits",
    [((5, 1),), (None,), (Limit(5, 1), (5, 1)), (Limit(5, 1), None)],
)
def test_ac036_non_limit_entry_in_tier_is_type_error(limits) -> None:
    with pytest.raises(TypeError) as excinfo:
        Tier("X", limits)

    assert type(excinfo.value) is TypeError
    assert str(excinfo.value).startswith("limits:")
