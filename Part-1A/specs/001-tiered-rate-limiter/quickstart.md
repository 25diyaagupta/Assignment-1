# Quickstart: validating the Tiered Token-Bucket Rate Limiter

## Prerequisites

- CPython 3.12 (`python3.12 --version` shows 3.12.x).
- Run everything from the repository root, `Part-1A/`.

## Setup

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

## Run all gates

```bash
.harness/run.sh          # runs G1–G13 from the constitution; exit 0 means all pass
```

Expected result: one PASS line per gate, then `ALL GATES PASSED`, with exit code 0.

## Smoke scenario (proves the feature end to end)

This reproduces AC-009, AC-010, AC-015 and AC-027 interactively, using the API in
[contracts/public-api.md](contracts/public-api.md).

1. Create `LimiterConfig` with tier `"layered"`, which has two limits:
   - `Limit(5, 5)`
   - `Limit(10, Fraction(1, 6))`
2. Create `TieredLimiter` with a fake clock that has a settable `t`.
3. Call `acquire("c1", "layered")` six times at `t=0`, six times at `t=1`, and once at `t=2`.

Expected results:

| Step | Expected |
|------|----------|
| `t=0` | 5 allowed, then 1 denied |
| `t=1` | 5 allowed, then 1 denied |
| `t=2` | denied, with `retry_after == 4` |
| `inspect("c1", "layered")` at `t=2` | `(5, Fraction(1, 3))` |
| `to_http(<t=2 decision>)` | `HttpOutcome(429, {"Retry-After": "4"})` |

## Performance metric (reported, not gated)

```bash
python bench/bench_decisions.py   # prints the time for 100,000 decisions across 10,000 clients (SC-005)
```
