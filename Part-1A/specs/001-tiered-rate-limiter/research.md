# Research: Tiered Token-Bucket Rate Limiter

All Technical Context unknowns are resolved below. Each entry follows Decision / Rationale /
Alternatives considered.

## R1. Numeric representation

- **Decision**:
  - Capacity and cost are `int`.
  - Refill rates, clock readings, balances and waits are `int | fractions.Fraction`.
  - `bool`, `float`, `Decimal`, `str` and `None` are rejected with `TypeError`.
- **Rationale**:
  - FR-014 and constitution XVI require this.
  - AC-015 (`Retry-After` exactly "4") and AC-027 (balance exactly 1/3) need exact arithmetic;
    with floats, `1/6 + 1/6` and the 4-second wait can round to `4.000…1`, and the ceiling then
    gives "5".
  - `math.ceil(Fraction)` is exact.
- **Alternatives considered**:
  - Integer micro-tokens with nanosecond ticks: exact, but it makes integrators pick a scale and
    turns AC-027's "1/3" into a rounding question.
  - `Decimal`: exact only for decimal fractions, so 1/6 is not exact. Rejected.

## R2. Clock interface

- **Decision**:
  - `Clock` is a `typing.Protocol` with one method, `now() -> int | Fraction`, returning seconds.
  - The production adapter `MonotonicClock` returns `Fraction(time.monotonic_ns(), 10**9)`.
  - Tests use a `FakeClock` with a settable `t`.
- **Rationale**:
  - Constitution IV and AC-026/AC-032 require it.
  - A monotonic source avoids wall-clock jumps.
  - Integer nanoseconds over 10⁹ keep FR-014's exact readings.
  - `clock.py` is the only module allowed to import `time`.
- **Alternatives considered**:
  - Passing `now` as an argument on every call: simpler, but it moves clock handling into every
    caller and makes AC-032 meaningless.
  - `time.time()`: the wall clock can jump backwards.

## R3. Time going backwards

- **Decision**: `elapsed = max(0, now - last_seen)` and `last_seen = max(last_seen, now)`.
- **Rationale**: This satisfies AC-007: there is no refill, no error, and refill later resumes
  from the latest reading seen.
- **Alternatives considered**:
  - Raising an error breaks AC-007.
  - Resetting `last_seen` to the earlier time would double-count refill.

## R4. Multi-limit decisions (layered tiers)

- **Decision**:
  - Refill every limit of the tier to `now`.
  - Allow the request only if every balance is at least the cost; then subtract the cost from
    all of them.
  - Otherwise leave every balance unchanged (refill is stored, nothing is subtracted) and set the
    wait to `max((cost - balance) / rate)` over the blocking limits.
- **Rationale**: This satisfies FR-004, FR-006, AC-009, AC-010 and AC-015. Storing the refill on a
  denial is safe because refill is idempotent for a given `now`.
- **Alternatives considered**: Consuming limit by limit and rolling back is more complex and risks
  partial consumption, which AC-010 forbids.

## R5. State keying

- **Decision**:
  - State is kept per `(client_key, tier_name)`, as a tuple of `BucketState`, one per limit.
  - It is created lazily, full, on first evaluation.
  - `inspect` never creates or changes state; for a client it has not seen, it reports full
    capacities.
- **Rationale**: FR-001, FR-002, FR-015 and AC-006 require this. Keying by tier as well means that
  if a client moves tier, the new tier's limits start fresh instead of reusing the old ones.
- **Alternatives considered**: Keying by client only would make the state wrong when a client
  changes tier.

## R6. Error contract

- **Decision**:
  - Wrong type: `TypeError`.
  - Wrong value: `ValueError`.
  - Domain subclasses: `UnknownTierError(ValueError)` and `CostExceedsCapacityError(ValueError)`.
  - Every message starts with the field name, for example `"capacity: must be int, got float"`.
- **Rationale**:
  - Constitution XIII and FR-009, FR-010 and FR-013 require this.
  - AC-029 asks for an error naming the field.
  - Validation happens before any state is touched, so "no tokens taken" holds by construction.
- **Alternatives considered**: A single `RateLimitConfigError` hides the type/value split that
  callers usually test for.

## R7. HTTP mapping

- **Decision**:
  - `to_http(decision) -> HttpOutcome(status, headers)`.
  - For an allowed decision: `(200, {})`.
  - For a denied decision: `(429, {"Retry-After": str(max(1, ceil(wait)))})`.
  - The module is named `http_mapping.py` so that it does not shadow the standard library's
    `http`.
- **Rationale**: This satisfies FR-007 and AC-012 to AC-017. RFC 9110 §10.2.3 allows
  `Retry-After` as delay-seconds (a non-negative decimal integer).
- **Alternatives considered**: An HTTP-date `Retry-After` needs the wall clock, which violates
  Principle IV.

## R8. Tooling (dev-only dependencies)

- **Decision**:
  - pytest, coverage, ruff, bandit, mypy, pip-audit and detect-secrets, pinned to exact versions
    in `requirements-dev.txt`.
  - They are installed in `.venv` created with `python3.12 -m venv`.
  - No runtime dependencies.
- **Rationale**:
  - Each tool backs a constitution gate (plan §Dependency Justification).
  - Versions are resolved at the registry during setup (task T001) and frozen. They are not
    guessed in this plan.
- **Alternatives considered**:
  - hypothesis for the SC-001 property test: rejected, because a seeded scripted generator in the
    tests gives the same coverage with no extra dependency and stays reproducible.
  - pytest-cov: rejected; running `coverage run` directly is enough.
  - gitleaks: rejected, because it is a non-Python binary. detect-secrets installs with pip.

## R9. AC tagging in tests

- **Decision**:
  - A custom marker `@pytest.mark.ac("AC-nnn", ...)` is registered in `pyproject.toml`.
  - `.harness/check_traceability.py` uses AST to collect marker arguments from `tests/` and the
    `**AC-nnn**` IDs from `spec.md`, then reports any orphans either way.
- **Rationale**: Constitution III requires this. Using a marker rather than test names allows one
  test to cover several ACs.
- **Alternatives considered**: Encoding the AC IDs in test names is brittle once a test covers
  more than one AC.

## R10. Reverse-order run and performance metric

- **Decision**:
  - `tests/conftest.py` reverses collection order when `HARNESS_REVERSE=1`.
  - The harness runs pytest twice, once in each order.
  - SC-005 is measured by `bench/bench_decisions.py`, which is reported and not gated.
- **Rationale**: Constitution XII requires the two-order run. The spec addendum says SC-005 does
  not gate acceptance.
