"""User Story 2: per-tier and layered limits (AC-008 to AC-011, AC-027).

Free = (5, 1/s); Pro = (20, 10/s); Layered = A (5, 5/s) and B (10, 1/6 token/s).
"""

from fractions import Fraction

import pytest

from tiered_limiter import UnknownTierError

LAYERED = "Layered"


def _drive_ac009(limiter, fake_clock) -> list[list[bool]]:
    """Run the AC-009 script and return the decisions per clock reading."""
    outcomes = []
    for t, n in ((0, 6), (1, 6), (2, 1)):
        fake_clock.t = t
        outcomes.append([limiter.acquire("c", LAYERED).allowed for _ in range(n)])
    return outcomes


@pytest.mark.ac("AC-008")
@pytest.mark.parametrize(("tier_name", "capacity"), [("Free", 5), ("Pro", 20)])
def test_ac008_new_client_21_requests_at_t0_first_capacity_allowed(
    make_limiter, free, pro, tier_name, capacity
):
    limiter = make_limiter(free, pro)
    got = [limiter.acquire("c", tier_name).allowed for _ in range(21)]
    assert got == [True] * capacity + [False] * (21 - capacity)


@pytest.mark.ac("AC-008")
def test_ac008_free_and_pro_clients_side_by_side(make_limiter, free, pro):
    limiter = make_limiter(free, pro)
    free_got = [limiter.acquire("f", "Free").allowed for _ in range(21)]
    pro_got = [limiter.acquire("p", "Pro").allowed for _ in range(21)]
    assert free_got.count(True) == 5
    assert pro_got.count(True) == 20
    assert free_got == [True] * 5 + [False] * 16
    assert pro_got == [True] * 20 + [False]


@pytest.mark.ac("AC-009")
def test_ac009_layered_allow_deny_sequence(make_limiter, layered, fake_clock):
    limiter = make_limiter(layered)
    assert _drive_ac009(limiter, fake_clock) == [
        [True] * 5 + [False],
        [True] * 5 + [False],
        [False],
    ]


@pytest.mark.ac("AC-010")
def test_ac010_denial_by_limit_b_takes_nothing_from_limit_a(
    make_limiter, layered, fake_clock
):
    limiter = make_limiter(layered)
    assert _drive_ac009(limiter, fake_clock)[2] == [False]
    assert limiter.inspect("c", LAYERED)[0] == 5


@pytest.mark.ac("AC-027")
def test_ac027_inspect_at_t2_exact_balances_and_read_only(
    make_limiter, layered, fake_clock
):
    limiter = make_limiter(layered)
    _drive_ac009(limiter, fake_clock)
    first = limiter.inspect("c", LAYERED)
    assert first == (5, Fraction(1, 3))
    assert limiter.inspect("c", LAYERED) == first


@pytest.mark.ac("AC-011")
def test_ac011_unknown_tier_raises_naming_tier(make_limiter, free, pro, layered):
    limiter = make_limiter(free, pro, layered)
    with pytest.raises(UnknownTierError, match="Gold") as excinfo:
        limiter.acquire("c", "Gold")
    assert str(excinfo.value).startswith("tier_name:")
    assert isinstance(excinfo.value, ValueError)
