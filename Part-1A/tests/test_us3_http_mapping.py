"""User Story 3: turn a decision into an HTTP response (AC-012 to AC-017).

Source: spec.md User Story 3 and contracts/public-api.md (`to_http` row).
Allowed -> HttpOutcome(200, {}); denied -> 429 with
Retry-After = str(max(1, ceil(retry_after))).
"""

import re
from fractions import Fraction

import pytest

from tiered_limiter import Decision, to_http

DIGITS = re.compile(r"[0-9]+")


@pytest.mark.ac("AC-012")
def test_ac012_allowed_decision_maps_to_200_without_retry_after() -> None:
    outcome = to_http(Decision(allowed=True, retry_after=0))

    assert outcome.status == 200
    assert "Retry-After" not in outcome.headers
    assert dict(outcome.headers) == {}


@pytest.mark.ac("AC-013")
@pytest.mark.parametrize(
    ("retry_after", "expected"),
    [
        (1, "1"),
        (Fraction(3, 4), "1"),
        (2, "2"),
        (Fraction(20001, 10000), "3"),
    ],
)
def test_ac013_denied_wait_rounds_up_to_whole_second(retry_after, expected) -> None:
    outcome = to_http(Decision(allowed=False, retry_after=retry_after))

    assert outcome.status == 429
    assert outcome.headers["Retry-After"] == expected


@pytest.mark.ac("AC-014")
def test_ac014_tiny_wait_maps_to_minimum_of_one_second() -> None:
    outcome = to_http(Decision(allowed=False, retry_after=Fraction(1, 1000)))

    assert outcome.status == 429
    assert outcome.headers["Retry-After"] == "1"


@pytest.mark.ac("AC-015")
def test_ac015_layered_denial_uses_longest_blocking_wait(
    fake_clock, layered, make_limiter
) -> None:
    limiter = make_limiter(layered)
    # AC-009 sequence. t=0: A 5->0, B 10->5; the 6th is denied by A.
    fake_clock.t = 0
    first = [limiter.acquire("c", "Layered") for _ in range(6)]
    # t=1: A refills to 5, B = 5 + 1/6; 5 allowed leaves B = 1/6.
    fake_clock.t = 1
    second = [limiter.acquire("c", "Layered") for _ in range(6)]
    # t=2: A = 5, B = 1/3; B needs 2/3 token at 1/6 token/s -> 4 s.
    fake_clock.t = 2
    denied = limiter.acquire("c", "Layered")

    assert [d.allowed for d in first] == [True] * 5 + [False]
    assert [d.allowed for d in second] == [True] * 5 + [False]
    assert denied.allowed is False
    assert denied.retry_after == 4
    outcome = to_http(denied)
    assert outcome.status == 429
    assert outcome.headers["Retry-After"] == "4"


@pytest.mark.ac("AC-016")
@pytest.mark.parametrize(
    ("deny_at", "cost", "expected_n"),
    [
        (0, 1, 1),
        (Fraction(1, 2), 1, 1),
        (Fraction(1, 3), 3, 3),
        (Fraction(9, 10), 5, 5),
        (Fraction(1, 1000), 1, 1),
    ],
)
def test_ac016_retry_after_n_seconds_is_allowed(
    fake_clock, free, make_limiter, deny_at, cost, expected_n
) -> None:
    limiter = make_limiter(free)
    fake_clock.t = 0
    drained = [limiter.acquire("c", "Free") for _ in range(5)]
    assert all(d.allowed for d in drained)

    fake_clock.t = deny_at
    denied = limiter.acquire("c", "Free", cost)
    assert denied.allowed is False
    outcome = to_http(denied)
    assert outcome.status == 429
    n = int(outcome.headers["Retry-After"])
    assert n == expected_n

    fake_clock.t = deny_at + n
    assert limiter.acquire("c", "Free", cost).allowed is True


@pytest.mark.ac("AC-017")
@pytest.mark.parametrize(
    "retry_after",
    [
        Fraction(1, 10**9),
        Fraction(1, 2),
        1,
        Fraction(3, 2),
        Fraction(20001, 10000),
        4,
        Fraction(99999, 7),
        10**6,
    ],
)
def test_ac017_retry_after_is_only_decimal_digits(retry_after) -> None:
    value = to_http(Decision(allowed=False, retry_after=retry_after)).headers[
        "Retry-After"
    ]

    assert DIGITS.fullmatch(value) is not None
    assert int(value) >= 1


@pytest.mark.ac("AC-017")
@pytest.mark.parametrize("cost", [1, 2, 3, 4, 5])
@pytest.mark.parametrize("deny_at", [0, Fraction(1, 7), Fraction(1, 2), Fraction(5, 6)])
def test_ac017_limiter_denials_give_digit_only_retry_after(
    fake_clock, free, make_limiter, cost, deny_at
) -> None:
    limiter = make_limiter(free)
    fake_clock.t = 0
    for _ in range(5):
        limiter.acquire("c", "Free")

    fake_clock.t = deny_at
    denied = limiter.acquire("c", "Free", cost)
    assert denied.allowed is False
    value = to_http(denied).headers["Retry-After"]

    assert DIGITS.fullmatch(value) is not None
    assert int(value) >= 1
