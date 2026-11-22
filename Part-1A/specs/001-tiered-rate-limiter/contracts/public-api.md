# Contract: Public API of `tiered_limiter`

`tiered_limiter.__all__` MUST equal exactly this set (constitution XIV):

```text
Clock, MonotonicClock, Limit, Tier, LimiterConfig, TieredLimiter, Decision,
HttpOutcome, to_http, UnknownTierError, CostExceedsCapacityError
```

Field types and constraints are defined in [data-model.md](../data-model.md) and are not repeated
here.

## Signatures

```text
class Clock(Protocol):
    def now(self) -> int | Fraction            # seconds; exact rational

class MonotonicClock:                          # the only code that reads the system clock
    def now(self) -> Fraction                  # Fraction(time.monotonic_ns(), 10**9)

Limit(capacity: int, refill_rate: int | Fraction)
Tier(name: str, limits: tuple[Limit, ...])
LimiterConfig(tiers: tuple[Tier, ...])

class TieredLimiter:                           # NOT thread-safe (FR-012): caller serialises access
    def __init__(self, config: LimiterConfig, clock: Clock) -> None
    def acquire(self, client_key: str, tier_name: str, cost: int = 1) -> Decision
    def inspect(self, client_key: str, tier_name: str) -> tuple[int | Fraction, ...]

Decision(allowed: bool, retry_after: int | Fraction)
HttpOutcome(status: int, headers: Mapping[str, str])
def to_http(decision: Decision) -> HttpOutcome

class UnknownTierError(ValueError)
class CostExceedsCapacityError(ValueError)
```

## Behavioural contract

| Call | Guarantee | Spec |
|------|-----------|------|
| `acquire` | All inputs are validated first. On error, no state changes. | FR-009, AC-023, AC-028–AC-031 |
| `acquire` | Reads `clock.now()` exactly once per call. Never reads system time. | FR-008, AC-026, AC-032 |
| `acquire` | Allows the request only if every limit holds at least `cost`; when it does, takes the cost from all of them. Otherwise nothing is subtracted. | FR-004, AC-009, AC-010 |
| `acquire` | When denied, `retry_after` is the maximum over the blocking limits of `(cost − balance) / rate`. | FR-006, AC-015 |
| `inspect` | Returns the balances refilled to `clock.now()`, in the tier's limit order. Never changes or creates state. For a client it has not seen, returns the full capacities. | FR-015, AC-027 |
| `to_http` | Allowed: `HttpOutcome(200, {})`. Denied: `HttpOutcome(429, {"Retry-After": str(max(1, ceil(retry_after)))})`. | FR-007, AC-012–AC-017 |

## Errors

| Condition | Exception | Message starts with |
|-----------|-----------|---------------------|
| wrong type (`bool`, `float`, `str`, `None`, …) | `TypeError` | the field name, e.g. `cost:` |
| non-positive capacity, rate or cost; empty name or key; empty tier list; duplicate tier | `ValueError` | the field name |
| unknown tier | `UnknownTierError` | `tier_name:` |
| cost > capacity of any limit | `CostExceedsCapacityError` | `cost:` (message includes both the cost and the capacity) |
