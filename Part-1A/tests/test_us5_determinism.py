"""User Story 5: deterministic decisions driven only by the injected clock.

Covers AC-025 (repeatable decisions, backs SC-003), AC-026 (time comes only from
the supplied clock), AC-032 (system time functions are never called) and AC-034
(no client exceeds capacity + rate x T in any window, backs SC-001).

Randomness lives only in the input generation, seeded with ``random.Random(2026)``.
"""

import datetime
import random
import time
from fractions import Fraction

import pytest

from tiered_limiter import LimiterConfig, TieredLimiter

SEED = 2026

# (capacity, refill rate) per limit, in tier order, as given in spec.md.
TIER_LIMITS = {
    "Free": ((5, 1),),
    "Pro": ((20, 10),),
    "Layered": ((5, 5), (10, Fraction(1, 6))),
}
TIER_NAMES = ("Free", "Pro", "Layered")


def generate_inputs(n_requests, n_clients):
    """Return scripted (time, client_key, tier_name, cost) tuples.

    Times are exact Fractions that never decrease. Each client keeps one tier,
    and each cost is between 1 and the smallest capacity of that tier.
    """
    rng = random.Random(SEED)
    tier_of = {f"client-{i:03d}": rng.choice(TIER_NAMES) for i in range(n_clients)}
    clients = sorted(tier_of)
    t = Fraction(0)
    inputs = []
    for _ in range(n_requests):
        t += Fraction(rng.randint(0, 3), rng.choice((60, 100, 120)))
        key = rng.choice(clients)
        tier_name = tier_of[key]
        max_cost = min(cap for cap, _ in TIER_LIMITS[tier_name])
        inputs.append((t, key, tier_name, rng.randint(1, max_cost)))
    return inputs


def run_script(limiter, clock, inputs):
    """Feed inputs to the limiter, returning (allowed, retry_after) per input."""
    decisions = []
    for t, key, tier_name, cost in inputs:
        clock.t = t
        decision = limiter.acquire(key, tier_name, cost)
        decisions.append((decision.allowed, decision.retry_after))
    return decisions


def accepted_cost_by_time(inputs, decisions):
    """Group accepted cost per client and per distinct time (times ascending)."""
    per_client = {}
    for (t, key, tier_name, cost), (allowed, _) in zip(inputs, decisions, strict=True):
        if not allowed:
            continue
        _, by_time = per_client.setdefault(key, (tier_name, {}))
        by_time[t] = by_time.get(t, 0) + cost
    return per_client


def window_violations(key, by_time, capacity, rate):
    """Check every pair t_i <= t_j: cost in [t_i, t_j] <= capacity + rate*(t_j - t_i).

    With prefix sums P, the cost in [t_i, t_j] is P[j+1] - P[i]. Rearranged, the
    bound is (P[j+1] - rate*t_j) - (P[i] - rate*t_i) <= capacity, exact.
    """
    times = sorted(by_time)
    prefix = [0]
    for t in times:
        prefix.append(prefix[-1] + by_time[t])
    upper = [prefix[j + 1] - rate * t for j, t in enumerate(times)]
    lower = [prefix[i] - rate * t for i, t in enumerate(times)]
    violations = []
    for i, low in enumerate(lower):
        for j in range(i, len(times)):
            if upper[j] - low > capacity:
                cost = prefix[j + 1] - prefix[i]
                violations.append((key, capacity, rate, times[i], times[j], cost))
    return violations


@pytest.mark.ac("AC-025")
def test_ac025_hundred_runs_give_identical_decisions(fake_clock, free, pro, layered):
    inputs = generate_inputs(n_requests=1_000, n_clients=20)
    tiers = (free, pro, layered)
    clock_type = type(fake_clock)
    runs = []
    for _ in range(100):
        clock = clock_type()
        limiter = TieredLimiter(LimiterConfig(tiers), clock)
        runs.append(run_script(limiter, clock, inputs))
    first = runs[0]
    assert len(first) == 1_000
    assert all(run == first for run in runs)
    first_bytes = repr(first).encode()
    assert all(repr(run).encode() == first_bytes for run in runs)


@pytest.mark.ac("AC-034")
def test_ac034_no_window_exceeds_capacity_plus_rate_times_length(
    fake_clock, make_limiter, free, pro, layered
):
    inputs = generate_inputs(n_requests=10_000, n_clients=100)
    limiter = make_limiter(free, pro, layered)
    decisions = run_script(limiter, fake_clock, inputs)
    per_client = accepted_cost_by_time(inputs, decisions)
    assert len({key for _, key, _, _ in inputs}) == 100
    violations = []
    for key, (tier_name, by_time) in sorted(per_client.items()):
        for capacity, rate in TIER_LIMITS[tier_name]:
            violations.extend(window_violations(key, by_time, capacity, rate))
    assert violations == []


@pytest.mark.ac("AC-026")
def test_ac026_decisions_follow_only_the_supplied_clock(fake_clock, make_limiter, free):
    limiter = make_limiter(free)
    fake_clock.t = 0
    for expected_calls in range(1, 6):
        assert limiter.acquire("alice", "Free").allowed is True
        assert fake_clock.calls == expected_calls
    assert limiter.acquire("alice", "Free").allowed is False
    assert fake_clock.calls == 6
    fake_clock.t = 1
    assert limiter.acquire("alice", "Free").allowed is True
    assert fake_clock.calls == 7


def patch_system_time(monkeypatch):
    """Make the system time functions raise and count every call to them."""
    calls = {
        "time.time": 0,
        "time.monotonic": 0,
        "time.monotonic_ns": 0,
        "datetime.now": 0,
    }

    def forbidden(name):
        def fail(*args, **kwargs):
            calls[name] += 1
            raise AssertionError(f"{name} was called")

        return fail

    class NoNowDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            calls["datetime.now"] += 1
            raise AssertionError("datetime.now was called")

    monkeypatch.setattr(time, "time", forbidden("time.time"))
    monkeypatch.setattr(time, "monotonic", forbidden("time.monotonic"))
    monkeypatch.setattr(time, "monotonic_ns", forbidden("time.monotonic_ns"))
    monkeypatch.setattr(datetime, "datetime", NoNowDatetime)
    return calls


@pytest.mark.ac("AC-026", "AC-032")
def test_ac026_ac032_system_time_never_read(
    monkeypatch, fake_clock, make_limiter, free, pro, layered
):
    limiter = make_limiter(free, pro, layered)
    calls = patch_system_time(monkeypatch)
    fake_clock.t = 0
    allowed = [limiter.acquire("alice", "Free").allowed for _ in range(6)]
    assert allowed == [True] * 5 + [False]
    assert limiter.acquire("bob", "Pro", 20).allowed is True
    assert limiter.acquire("carol", "Layered", 5).allowed is True
    fake_clock.t = Fraction(3, 2)
    assert limiter.acquire("alice", "Free").allowed is True
    assert limiter.acquire("bob", "Pro", 15).allowed is True
    assert fake_clock.calls == 10
    assert limiter.inspect("alice", "Free") == (Fraction(1, 2),)
    assert calls == {
        "time.time": 0,
        "time.monotonic": 0,
        "time.monotonic_ns": 0,
        "datetime.now": 0,
    }
