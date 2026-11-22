"""User Story 1: limit a client with a token bucket (AC-001 to AC-007).

Free tier = capacity 5, refill 1 token/s (spec.md, User Story 1).
"""

from fractions import Fraction

import pytest

from tiered_limiter import TieredLimiter

FREE = "Free"


def _run(limiter: TieredLimiter, client: str, n: int, cost: int = 1) -> list[bool]:
    return [limiter.acquire(client, FREE, cost).allowed for _ in range(n)]


@pytest.mark.ac("AC-001")
def test_ac001_new_free_client_five_requests_at_t0_all_allowed(make_limiter, free):
    limiter = make_limiter(free)
    assert _run(limiter, "alice", 5) == [True] * 5


@pytest.mark.ac("AC-002")
def test_ac002_sixth_request_at_t0_denied(make_limiter, free):
    limiter = make_limiter(free)
    assert _run(limiter, "alice", 5) == [True] * 5
    assert limiter.acquire("alice", FREE).allowed is False


@pytest.mark.ac("AC-003")
@pytest.mark.parametrize(
    ("t", "expected"),
    [(Fraction("0.999"), False), (1, True)],
    ids=["t0.999-denied", "t1-allowed"],
)
def test_ac003_empty_bucket_refills_one_token_after_one_second(
    make_limiter, free, fake_clock, t, expected
):
    limiter = make_limiter(free)
    assert _run(limiter, "alice", 5) == [True] * 5
    fake_clock.t = t
    assert limiter.acquire("alice", FREE).allowed is expected


@pytest.mark.ac("AC-004")
@pytest.mark.parametrize("seen_at_t0", [False, True], ids=["unseen", "seen-at-t0"])
def test_ac004_idle_until_t1000_exactly_first_five_allowed(
    make_limiter, free, fake_clock, seen_at_t0
):
    limiter = make_limiter(free)
    if seen_at_t0:
        assert limiter.acquire("alice", FREE).allowed is True
    fake_clock.t = 1000
    assert _run(limiter, "alice", 6) == [True] * 5 + [False]


@pytest.mark.ac("AC-005")
def test_ac005_cost_above_balance_denied_takes_nothing_then_exact_cost_allowed(
    make_limiter, free
):
    limiter = make_limiter(free)
    assert _run(limiter, "alice", 2) == [True, True]
    assert limiter.inspect("alice", FREE) == (3,)
    assert limiter.acquire("alice", FREE, 4).allowed is False
    assert limiter.inspect("alice", FREE) == (3,)
    assert limiter.acquire("alice", FREE, 3).allowed is True
    assert limiter.inspect("alice", FREE) == (0,)


@pytest.mark.ac("AC-006")
def test_ac006_clients_are_independent(make_limiter, free):
    limiter = make_limiter(free)
    assert _run(limiter, "A", 6) == [True] * 5 + [False]
    assert limiter.acquire("B", FREE).allowed is True
    assert limiter.inspect("A", FREE) == (0,)
    assert limiter.inspect("B", FREE) == (4,)


@pytest.mark.ac("AC-007")
def test_ac007_clock_backwards_no_error_no_refill_then_refill_from_t10(
    make_limiter, free, fake_clock
):
    limiter = make_limiter(free)
    fake_clock.t = 10
    assert _run(limiter, "alice", 5) == [True] * 5
    fake_clock.t = 5
    assert limiter.acquire("alice", FREE).allowed is False
    assert limiter.inspect("alice", FREE) == (0,)
    fake_clock.t = 11
    assert limiter.inspect("alice", FREE) == (1,)
    assert limiter.acquire("alice", FREE).allowed is True
    assert limiter.inspect("alice", FREE) == (0,)
