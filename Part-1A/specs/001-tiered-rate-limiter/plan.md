# Implementation Plan: Tiered Token-Bucket Rate Limiter

**Branch**: `main` (spec dir `001-tiered-rate-limiter`) | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-tiered-rate-limiter/spec.md` (Approved, AC-001–AC-036)

**Scope**: lean scope (constitution v1.0.2, 2026-11-22). Every FR, SC and AC in spec.md is
unchanged. SC-004 and SC-005 have no task in this scope and are not measured.

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

**Target Platform**: any OS that runs CPython 3.12. The harness is a set of bash scripts for Linux.

**Project Type**: library

**Performance Goals**: SC-005 (100,000 decisions across 10,000 clients in under 1 s) is not
measured in the lean scope.

**Constraints**:
- Functions are at most 40 lines (review), with cyclomatic complexity at most 10 (ruff `C901`).
- Branch coverage is at least 90 %.
- Ruff and Bandit report zero findings, with no suppressions. Ruff checks `src/` with the full
  rule set and `tests/` with the smaller set in §Ruff Rule Sets.
- The limiter is not thread-safe (FR-012).

**Scale/Scope**: 7 source modules plus `__init__.py`, 36 ACs (AC-001–AC-036), and memory that
grows linearly with the number of distinct `(client, tier)` pairs (no eviction in v1)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (see the end).*

"Review" means the Governance review checklist in constitution v1.0.2, not a harness gate.

| # | Principle | How this plan satisfies it | Status |
|---|-----------|----------------------------|--------|
| I | Py 3.12, standard library core | No runtime dependencies. Every dev tool is justified below. `requires-python = ">=3.12,<3.13"`. Import purity of `src/` is checked at review. | PASS |
| II | Zero lint/security findings, no suppressions | G3 runs ruff on `src tests`: full set from `pyproject.toml` on `src/`, the smaller set from `tests/ruff.toml` on `tests/` (§Ruff Rule Sets). Neither ignores any rule. G2 searches `*.py` files for suppression comment syntax with `rg`. G4 runs Bandit on `src/`. | PASS |
| III | Binary, traceable ACs | Every test carries `@pytest.mark.ac`. Traceability is checked by hand at T017 and at review. **See Required Spec Amendment.** | PASS |
| IV | Injected clock | `Clock` protocol. `time` is imported only in `clock.py` (review). AC-026 and AC-032 patch `time.*` and `datetime.now`. | PASS |
| V | ≤ 40 lines, CC ≤ 10 | Pure functions in `bucket.py` and validators in `_validate.py` keep units small. Complexity: ruff `C901` in G3. Length: review. | PASS |
| VI | Branch coverage ≥ 90 % | G5: `coverage run --branch -m pytest`, then `coverage report --fail-under=90`, with nothing in `src/` omitted. | PASS |
| VII | No secrets | No credentials are needed. G6 runs `detect-secrets scan` over the working tree. Git history is not scanned (v1.0.2). | PASS |
| VIII | Protected tests/harness | Tagged `harness-approved`. G1 fails if `git diff --name-only harness-approved..HEAD -- tests .harness` is non-empty. | PASS |
| IX | Spec changes via Spec Kit | Only spec.md, plan.md and tasks.md change, each with a dated change note. | PASS |
| X | Baseline plus 2 repairs | Tagged `impl-baseline`. The number of `repair(` commits is checked at review. | PASS |
| XI | Static typing | Full annotations, enforced by ruff `ANN` in G3. mypy is not run (v1.0.2). | PASS |
| XII | Hermetic tests in under 10 s | Fake clock, no I/O. G5 prints the suite time, which is checked at review. No reverse-order run (v1.0.2). | PASS |
| XIII | Explicit error contract | `TypeError` / `ValueError` plus 2 subclasses. No runtime `assert` in src. | PASS |
| XIV | Documented public API | Ruff `D` (Google convention). The `__all__` set is the list in §Public API below; [contracts/public-api.md](contracts/public-api.md) is derived from it. | PASS |
| XV | Pinned dependencies | `requirements-dev.txt` uses exact `==` pins. pip-audit is not run (v1.0.2). | PASS |
| XVI | Numeric determinism | `int` / `Fraction` only; no `float` in src (review). `Retry-After = max(1, ceil(wait))`, covered by AC-013–AC-015. | PASS |

No violations, so Complexity Tracking stays empty.

### Required Spec Amendment (before tests are written) — done 2026-11-22

Principle III forbids any test that does not cover an AC. These ACs were added to spec.md with a
dated change note:

- **AC-033**: `tiered_limiter.__all__` equals exactly the name set in
  `contracts/public-api.md`. This backs constitution XIV.
- **AC-034**: in the seeded scripted run of 10,000 requests across 100 clients, for every client,
  limit and pair of accepted requests at t_i ≤ t_j, the cost accepted in [t_i, t_j] is at most
  capacity + rate × (t_j − t_i). This backs SC-001.
- **AC-035**: an empty tier list raises `ValueError` (`tiers:`). This backs constitution XIII.
- **AC-036**: a non-`Limit` entry in `Tier.limits` raises `TypeError` (`limits:`). This backs
  constitution XIII.

### Public API (constitution XIV)

`tiered_limiter.__all__` is exactly these 11 names. This list is the source;
[contracts/public-api.md](contracts/public-api.md) is derived from it and must list the same set.

```text
Clock, MonotonicClock, Limit, Tier, LimiterConfig, TieredLimiter, Decision,
HttpOutcome, to_http, UnknownTierError, CostExceedsCapacityError
```

### Harness Gates (constitution v1.0.2)

| Gate | Check |
|------|-------|
| G1 Integrity | `git diff --name-only harness-approved..HEAD -- tests .harness` is empty. It passes with a warning before the tag exists. |
| G2 Suppressions | `rg --glob '*.py'` for `#\s*(noqa\|nosec\|type:\s*ignore\|pragma:\s*no\s*cover\|fmt:\s*off)` finds nothing (`.venv/` excluded). |
| G3 Lint/format | `ruff check src tests` and `ruff format --check src tests` report zero findings. |
| G4 Security | `bandit -r src` reports zero findings. |
| G5 Tests and coverage | `coverage run --branch -m pytest`, then `coverage report --fail-under=90`. Prints the wall time. |
| G6 Secrets | `detect-secrets scan` over the working tree reports zero findings. |
| G7 Self-check | `.harness/self_check.sh` builds one deliberately broken fake per gate (G1–G6) in a temporary directory and confirms that each gate fails on its fake. |

### Ruff Rule Sets (constitution II)

| Scope | Config | Selected rule families |
|-------|--------|------------------------|
| `src/` | `pyproject.toml` (`[tool.ruff.lint]`) | E, F, W, I, B, C90, D, ANN, S, UP, SIM, PL |
| `tests/` | `tests/ruff.toml` (`extend = "../pyproject.toml"`, own `select`) | E, F, W, I, B, C90, UP, SIM |

Omitted for `tests/`, with reasons:

- **S** (flake8-bandit): `S101` flags every pytest `assert`. Bandit (G4) still scans `src/`.
- **PL** (pylint): `PLR2004` flags the literal expected values that the ACs specify, and
  `PLR0913` flags fixture-heavy test signatures.
- **D** (docstrings): constitution XIV requires docstrings on the public API, not on tests. Test
  names and `ac` markers carry the traceability.
- **ANN** (annotations): constitution XI applies to `src/`. pytest fixtures injected by name gain
  nothing from annotations.

## Dependency Justification (Principle I)

All of these are dev-only. They are pinned to exact versions in `requirements-dev.txt`, resolved
at the registry in task T001.

| Package | Gate | Justification |
|---------|------|---------------|
| pytest | G5 | Test runner that the constitution names. It supports the custom `ac` marker. |
| coverage | G5 | Measures branch coverage for the ≥ 90 % threshold (Principle VI). |
| ruff | G3 | Lint, format, complexity (`C901`), docstrings (`D`) and annotations (`ANN`) (Principles II, V, XI, XIV). |
| bandit | G4 | The security scan that Principle II requires. |
| detect-secrets | G6 | Secret scan of the working tree (Principle VII). It installs with pip, so no extra binary is needed. |
| System tools (not pip-installed): `bash`, `git`, `rg` (ripgrep) | G1, G2, G7 | `bash` runs the harness; `git` supplies the G1 diff and the throwaway repository in the G7 fake; `rg` is the G2 search. They are taken from the OS and are not pinned. |

These were considered and rejected: hypothesis (a seeded generator is enough), pytest-cov
(redundant), gitleaks (a non-Python binary), mypy and pip-audit (removed in the lean scope).

## Project Structure

### Documentation (this feature)

```text
specs/001-tiered-rate-limiter/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: entities, fields, constraints
├── quickstart.md        # Phase 1: setup, gates, smoke scenario
├── contracts/
│   └── public-api.md    # Phase 1: __all__ (derived from §Public API), signatures, errors
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root = `Part-1A/`)

```text
pyproject.toml               # project metadata, ruff/coverage/pytest config (no ignores)
requirements-dev.txt         # exact pins for dev tools
src/tiered_limiter/
├── __init__.py              # __all__ (§Public API)
├── clock.py                 # Clock protocol, MonotonicClock (only module importing time)
├── _validate.py             # type/value checks: int-not-bool, rational, non-empty str
├── config.py                # Limit, Tier, LimiterConfig (+ validation)
├── errors.py                # UnknownTierError, CostExceedsCapacityError
├── bucket.py                # BucketState, refill, consume, wait_for (pure)
├── limiter.py               # TieredLimiter, Decision
└── http_mapping.py          # HttpOutcome, to_http

tests/                       # PROTECTED after tag harness-approved
├── ruff.toml                # smaller ruff rule set for tests/ (§Ruff Rule Sets)
├── conftest.py              # FakeClock fixture, example tier fixtures
├── test_us1_token_bucket.py     # AC-001–AC-007
├── test_us2_tiers.py            # AC-008–AC-011, AC-027
├── test_us3_http_mapping.py     # AC-012–AC-017
├── test_us4_validation.py       # AC-018–AC-024, AC-028–AC-031, AC-035, AC-036
├── test_us5_determinism.py      # AC-025, AC-026, AC-032, AC-034
└── test_public_api.py           # AC-033

.harness/                    # PROTECTED after tag harness-approved
├── gates.sh                 # functions gate_g1 … gate_g6, each taking a root directory
├── self_check.sh            # G7: broken fakes in a temp dir; every gate must fail on its fake
└── run.sh                   # runs G1–G7 on the repository, exit 0 only if all pass
```

**Structure Decision**: a single library project using the `src/` layout, so tests import the
installed package and not the working tree. Tests are grouped by user story, which matches the
spec phases and the AC ranges. The harness is bash only, so it contains no `*.py` file for ruff
or G2 to check.

## Post-Design Constitution Re-check

The design artefacts introduce no new dependency, no wall-clock access outside `clock.py`, and no
suppression. Every data-model field cites its FR/AC, and §Public API fixes the public API.

All 16 principles PASS under constitution v1.0.2. III, XIII and XIV rely on the Required Spec
Amendment (AC-033 to AC-036), which was made on 2026-11-22.

## Complexity Tracking

No violations; nothing to justify.

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude): applied `/speckit-analyze` fixes. Reason: align
  the plan with the analysis findings and constitution v1.0.1. Changes: §Ruff Rule Sets added
  (D1); G2 now matches only comment syntax in `*.py` files (D2); G11 scans every commit and fails
  on zero files (U1); system tools row added to §Dependency Justification (D3); AC range and count
  updated to AC-001–AC-036 (I3); `bench/check_readme_example.py` added for SC-004 (C3).
  Affected: AC-033, AC-034, AC-035, AC-036.
- **2026-11-22** (Deepanshi Bansal, with Claude): lean-scope update to match constitution
  v1.0.2. Reason: one-day deadline. Changes: harness cut to G1–G7 (§Harness Gates), with a new
  G7 self-check on broken fakes; history secret scan, checksum manifest, mypy, pip-audit,
  reverse-order hook, `bench/` (SC-004 README check and SC-005 benchmark) and the clock-purity,
  function-size, traceability, dependency and repair-budget scripts removed, with their checks
  moved to review where the constitution keeps them; `.harness/` and `bench/` are no longer
  ruff-checked. §Public API added as the source of the `__all__` list (analysis finding C1);
  module count corrected. Every FR, SC and AC is unchanged. Supersedes the first entry's G11
  and SC-004 changes. No AC IDs are affected.
