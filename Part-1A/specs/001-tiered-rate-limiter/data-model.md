# Data Model: Tiered Token-Bucket Rate Limiter

`Rational` means `int | fractions.Fraction`, with `bool` excluded. Every entity is an immutable
frozen dataclass with slots, except `TieredLimiter`, which holds mutable state. Validation runs in
`__post_init__` or at the start of the call, before any state changes.

## Limit

One token-bucket rule. Defined in `src/tiered_limiter/config.py`.

| Field | Type | Constraint | Error | Spec |
|-------|------|-----------|-------|------|
| `capacity` | `int` | `> 0`; `bool`, `float`, `Fraction`, `str` and `None` rejected | `TypeError` (type), `ValueError` (≤ 0) | FR-014, AC-018, AC-028–AC-030 |
| `refill_rate` | `Rational` (tokens/second) | `> 0`; `bool`, `float`, `str` and `None` rejected (NaN and inf are floats, so they are rejected too) | `TypeError` (type), `ValueError` (≤ 0) | FR-014, AC-019, AC-020, AC-028, AC-029 |

## Tier

A named set of limits. Defined in `src/tiered_limiter/config.py`.

| Field | Type | Constraint | Error | Spec |
|-------|------|-----------|-------|------|
| `name` | `str` | non-empty | `TypeError` (non-str), `ValueError` (empty) | FR-016, AC-031 |
| `limits` | `tuple[Limit, ...]` | length ≥ 1; every item is a `Limit` | `ValueError` (empty), `TypeError` (item) | AC-021 |

## LimiterConfig

The whole configuration. Defined in `src/tiered_limiter/config.py`.

| Field | Type | Constraint | Error | Spec |
|-------|------|-----------|-------|------|
| `tiers` | `tuple[Tier, ...]` | length ≥ 1; tier names unique | `ValueError` (duplicate names the tier) | AC-022 |

## BucketState (internal)

One client's balance for one limit. Defined in `src/tiered_limiter/bucket.py`.

| Field | Type | Constraint | Spec |
|-------|------|-----------|------|
| `balance` | `Rational` | `0 ≤ balance ≤ capacity` (invariant) | FR-003 |
| `last_seen` | `Rational` | non-decreasing (only `max(last_seen, now)` writes it) | FR-008, AC-007 |

State transitions (pure functions):
- `refill(state, limit, now)` produces `balance' = min(capacity, balance + max(0, now − last_seen) × rate)`
  and `last_seen' = max(last_seen, now)`.
- `consume(state, cost)` produces `balance' = balance − cost`. It is called only when
  `balance ≥ cost`.
- `wait_for(state, limit, cost)` returns `0` if `balance ≥ cost`, otherwise
  `(cost − balance) / rate`.

## Request inputs (per call to `acquire`)

| Field | Type | Constraint | Error | Spec |
|-------|------|-----------|-------|------|
| `client_key` | `str` | non-empty | `TypeError` / `ValueError` | FR-016, AC-031 |
| `tier_name` | `str` | non-empty; must name a configured tier | `TypeError` / `ValueError` / `UnknownTierError` | FR-010, FR-016, AC-011, AC-031 |
| `cost` | `int` (default 1) | `> 0`; `≤` capacity of every limit in the tier | `TypeError` / `ValueError` / `CostExceedsCapacityError` | FR-013, FR-014, AC-023, AC-024, AC-028–AC-030 |
| clock reading | `Rational` | type checked on every read | `TypeError` naming `clock reading` | FR-014 |

## Decision

The result of one call to `acquire`. Defined in `src/tiered_limiter/limiter.py`.

| Field | Type | Meaning |
|-------|------|---------|
| `allowed` | `bool` | `True` if the cost was taken from every limit |
| `retry_after` | `Rational` | `0` when allowed; when denied, the exact wait (> 0) until the same request could be allowed, which is the maximum over the blocking limits (FR-006, AC-015) |

## HttpOutcome

What the HTTP mapping returns. Defined in `src/tiered_limiter/http_mapping.py`.

| Field | Type | Meaning |
|-------|------|---------|
| `status` | `int` | `200` or `429` |
| `headers` | `Mapping[str, str]` | `{}` for 200; `{"Retry-After": "<digits>"}` for 429, where the value is `max(1, ceil(retry_after))` (AC-013, AC-014, AC-017) |

## Relationships

- `LimiterConfig` has one or more `Tier`, and each `Tier` has one or more `Limit`.
- `TieredLimiter` maps each `(client_key, tier_name)` to a tuple of `BucketState`, one per limit
  of that tier, in the same order.
