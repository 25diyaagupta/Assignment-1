# Implementation Plan: Tiered Token-Bucket Rate Limiter

**Branch**: `main` (spec dir `001-tiered-rate-limiter`) | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-tiered-rate-limiter/spec.md` (Approved, AC-001–AC-032)

## Summary

The deliverable is a pure-Python, standard-library-only library made of three parts:

- **Tiered token buckets.** Each named tier has one or more limits, and a request is allowed only
  when every limit can pay its cost.
- **Exact rational arithmetic** (`int` and `Fraction`). This makes waits and balances exact, so
  `Retry-After` never rounds up by mistake at whole-second boundaries.
- **A mapping function** that turns a decision into HTTP 200, or 429 with `Retry-After`.

Time enters only through an injected `Clock`, which makes every decision deterministic. Decisions
are recorded in [research.md](research.md).

## Technical Context

**Language/Version**: CPython 3.12 (`python3.12`, available locally as 3.12.14)

**Primary Dependencies**: none at runtime (standard library: `fractions`, `math`, `dataclasses`,
`typing`, `time` in `clock.py` only). Dev tools are listed under Dependency Justification below.

**Storage**: N/A (state is kept in memory, per limiter instance)

**Testing**: pytest with a custom `ac` marker, plus `coverage` with branch measurement

**Target Platform**: any OS that runs CPython 3.12. The harness is a bash script for Linux.

**Project Type**: library

**Performance Goals**: SC-005, 100,000 decisions across 10,000 clients in under 1 s (reported,
not gated)

**Constraints**:
- Functions are at most 40 lines, with cyclomatic complexity at most 10.
- Branch coverage is at least 90 %.
- Ruff, Bandit and mypy `--strict` report zero findings, with no suppressions.
- The limiter is not thread-safe (FR-012).

**Scale/Scope**: about 6 source modules, about 32 ACs, and memory that grows linearly with the
number of distinct `(client, tier)` pairs (no eviction in v1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (see the end).*

| # | Principle | How this plan satisfies it | Status |
|---|-----------|----------------------------|--------|
| I | Py 3.12, standard library core | No runtime dependencies. Every dev tool is justified below. `requires-python = ">=3.12,<3.13"`. | PASS |
| II | Zero lint/security findings, no suppressions | The `pyproject.toml` ruff config selects rules and never ignores any. G2 searches for suppression comments with `rg`. | PASS |
| III | Binary, traceable ACs | The `@pytest.mark.ac` marker is checked by `.harness/check_traceability.py`. **See Required Spec Amendment.** | PASS (after amendment) |
| IV | Injected clock | `Clock` protocol. `time` is imported only in `clock.py`. G6 runs an AST scan. AC-032 patches `time.*` and `datetime.now`. | PASS |
| V | ≤ 40 lines, CC ≤ 10 | Pure functions in `bucket.py` and validators in `_validate.py` keep units small. Checked by G7 (AST script plus ruff `C901`). | PASS |
| VI | Branch coverage ≥ 90 % | `coverage run --branch`, then `coverage report --fail-under=90`, with nothing in `src/` omitted. | PASS |
| VII | No secrets | No credentials are needed. G11 runs `detect-secrets` over the tree and the history. | PASS |
| VIII | Protected tests/harness | Tagged `harness-approved`. G1 checks the git diff and the `.harness/MANIFEST.sha256` checksums. | PASS |
| IX | Spec changes via Spec Kit | Only spec.md, plan.md and tasks.md change, each with a dated change note. | PASS |
| X | Baseline plus 2 repairs | Tagged `impl-baseline`. G13 counts `repair(` commits. | PASS |
| XI | Static typing | Full annotations, `mypy --strict src`, ruff `ANN`. | PASS |
| XII | Hermetic, order-independent tests in under 10 s | Fake clock, no I/O. `HARNESS_REVERSE=1` reverses order in `tests/conftest.py`. | PASS |
| XIII | Explicit error contract | `TypeError` / `ValueError` plus 2 subclasses. No runtime `assert` in src. | PASS |
| XIV | Documented public API | Ruff `D` (Google convention). The `__all__` set is fixed in [contracts/public-api.md](contracts/public-api.md). | PASS (after amendment) |
| XV | Pinned, audited dependencies | `requirements-dev.txt` uses exact `==` pins. G12 runs `pip-audit -r requirements-dev.txt`. | PASS |
| XVI | Numeric determinism | `int` / `Fraction` only. G6 also scans for the `float` name in src. `Retry-After = max(1, ceil(wait))`. | PASS |

No violations, so Complexity Tracking stays empty.

### Required Spec Amendment (before tests are written)

Principle III forbids any test that does not cover an AC. Two planned tests have no AC yet, so
spec.md needs these two ACs, added with a dated change note:

- **AC-033**: `tiered_limiter.__all__` equals exactly the name set in
  `contracts/public-api.md`. This backs constitution XIV.
- **AC-034**: in the seeded scripted run of 10,000 requests across 100 clients, no client's
  accepted cost in any window of length T exceeds capacity + rate × T for any limit. This backs
  SC-001.

## Dependency Justification (Principle I)

All of these are dev-only. They are pinned to exact versions in `requirements-dev.txt`, resolved
at the registry in task T001.

| Package | Gate | Justification |
|---------|------|---------------|
| pytest | G9 | Test runner that the constitution names. It supports the custom `ac` marker. |
| coverage | G10 | Measures branch coverage for the ≥ 90 % threshold (Principle VI). |
| ruff | G3, G7 | Lint, format, complexity (`C901`), docstrings (`D`) and annotations (`ANN`) (Principles II, V, XI, XIV). |
| bandit | G4 | The security scan that Principle II requires. |
| mypy | G5 | `--strict` type checking (Principle XI). |
| pip-audit | G12 | Scans pinned dependencies for known vulnerabilities (Principle XV). |
| detect-secrets | G11 | Secret scan of the tree and the history (Principle VII). It installs with pip, so no extra binary is needed. |

These were considered and rejected: hypothesis (a seeded generator is enough), pytest-cov
(redundant), gitleaks (a non-Python binary).

## Project Structure

### Documentation (this feature)

```text
specs/001-tiered-rate-limiter/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: entities, fields, constraints
├── quickstart.md        # Phase 1: setup, gates, smoke scenario
├── contracts/
│   └── public-api.md    # Phase 1: __all__, signatures, error contract
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root = `Part-1A/`)

```text
pyproject.toml               # project metadata, ruff/mypy/coverage/pytest config (no ignores)
requirements-dev.txt         # exact pins for dev tools
src/tiered_limiter/
├── __init__.py              # __all__ (contract)
├── clock.py                 # Clock protocol, MonotonicClock (only module importing time)
├── _validate.py             # type/value checks: int-not-bool, rational, non-empty str
├── config.py                # Limit, Tier, LimiterConfig (+ validation)
├── errors.py                # UnknownTierError, CostExceedsCapacityError
├── bucket.py                # BucketState, refill, consume, wait_for (pure)
├── limiter.py               # TieredLimiter, Decision
└── http_mapping.py          # HttpOutcome, to_http

tests/                       # PROTECTED after tag harness-approved
├── conftest.py              # FakeClock fixture, ac marker, HARNESS_REVERSE ordering
├── test_us1_token_bucket.py     # AC-001–AC-007
├── test_us2_tiers.py            # AC-008–AC-011, AC-027
├── test_us3_http_mapping.py     # AC-012–AC-017
├── test_us4_validation.py       # AC-018–AC-024, AC-028–AC-031
├── test_us5_determinism.py      # AC-025, AC-026, AC-032, AC-034
└── test_public_api.py           # AC-033

.harness/                    # PROTECTED after tag harness-approved
├── run.sh                   # runs G1–G13 in order, exit 0 only if all pass
├── MANIFEST.sha256          # checksums of tests/ and .harness/ (except itself)
├── check_protection.sh      # G1
├── check_suppressions.sh    # G2
├── check_clock_purity.py    # G6 (+ float scan)
├── check_function_size.py   # G7
├── check_traceability.py    # G8
├── check_dependencies.py    # G12 (pins vs plan table)
└── check_repair_budget.sh   # G13

bench/bench_decisions.py     # SC-005 metric (not gated, not a test)
```

**Structure Decision**: a single library project using the `src/` layout, so tests import the
installed package and not the working tree. Tests are grouped by user story, which matches the
spec phases and the AC ranges.

## Post-Design Constitution Re-check

The design artefacts introduce no new dependency, no wall-clock access outside `clock.py`, and no
suppression. Every data-model field cites its FR/AC, and the contract fixes the public API.

All 16 principles PASS. III and XIV depend on the Required Spec Amendment (AC-033, AC-034) being
made before `/speckit-tasks` produces the test tasks.

## Complexity Tracking

No violations; nothing to justify.
