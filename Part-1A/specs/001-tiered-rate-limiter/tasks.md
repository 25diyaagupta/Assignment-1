---

description: "Task list for the Tiered Token-Bucket Rate Limiter"
---

# Tasks: Tiered Token-Bucket Rate Limiter

**Input**: Design documents from `specs/001-tiered-rate-limiter/`

**Prerequisites**: plan.md, spec.md (Approved), research.md, data-model.md,
contracts/public-api.md, quickstart.md

**Scope**: lean scope (constitution v1.0.2, 2026-11-22). The harness has 7 gates (plan.md
§Harness Gates). SC-004 and SC-005 have no task in this scope.

**Tests**: Required. Constitution III makes every AC need a test, and VIII makes the tests come
before the implementation.

**Organization**: Constitution VIII and X override the template's default ordering:

1. All tests and the harness for **every** story are written first (Phase 3).
2. They are approved and tagged `harness-approved` (Phase 4).
3. Then the implementation runs story by story (Phases 5–9).
4. The first full implementation is tagged `impl-baseline` **before** any repair driven by the
   harness (Phase 10).

Test tasks still carry their `[USn]` label, so each story stays traceable and can be tested on
its own.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: The user story the task belongs to (US1–US5)
- All paths are relative to the repository root, `Part-1A/`.
- Field constraints are cited as `data-model.md Entity.field`. Tasks restate a constraint only
  when they narrow it.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project skeleton, tool configuration and pinned dev dependencies

- [ ] T001 Create `.venv` with `python3.12 -m venv .venv`. Resolve the current versions of pytest, coverage, ruff, bandit and detect-secrets at the registry, then write exact `==` pins to `requirements-dev.txt`. Use only the packages in the plan.md §Dependency Justification table.
- [ ] T002 Create `pyproject.toml` with:
  - project `tiered-limiter` using the `src` layout, `requires-python = ">=3.12,<3.13"` and no runtime dependencies;
  - `[tool.ruff]` with target `py312`, and `[tool.ruff.lint]` with `select` rules E, F, W, I, B, C90, D, ANN, S, UP, SIM, PL, `[tool.ruff.lint.mccabe] max-complexity = 10` and `[tool.ruff.lint.pydocstyle] convention = "google"`. Add no `ignore`, `extend-ignore`, `per-file-ignores` or `exclude` entries;
  - `[tool.coverage]` with `branch = true`, `source = ["src"]`, `fail_under = 90` and no omit entries;
  - `[tool.pytest.ini_options]` that registers the `ac` marker and sets `--strict-markers`.

  Also create `tests/ruff.toml` with `extend = "../pyproject.toml"` and a `[lint]` `select` of E, F, W, I, B, C90, UP, SIM only, as plan.md §Ruff Rule Sets records. It has no `ignore`, `extend-ignore`, `per-file-ignores` or `exclude` entries.
- [ ] T003 [P] Create the package skeleton `src/tiered_limiter/__init__.py` with a module docstring and `__all__: list[str] = []`. No exports yet, so the tests fail on import.
- [ ] T004 [P] Add the virtual environment, cache and coverage entries (`.venv/`, `__pycache__/`, `.coverage`, `.ruff_cache/`, `.pytest_cache/`) to `.gitignore`.
- [ ] T005 Install the tools: `pip install -r requirements-dev.txt && pip install -e .`. Record the `pip freeze` output in the commit message, and confirm that `ruff check src tests` passes on the skeleton.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Spec amendment, test fixtures and harness gates. These come before any test or source
code.

**⚠️ CRITICAL**: No test or story work begins until this phase is complete.

- [X] T006 Amend `specs/001-tiered-rate-limiter/spec.md` (constitution IX). Done 2026-11-22: AC-033 to AC-036 added with a dated Change Notes entry, and the `Reason:` in the 2026-11-22 addendum entry is filled in.
  - **AC-033**: public API surface equals contracts/public-api.md;
  - **AC-034**: windowed accepted-cost bound for every pair of accepted requests;
  - **AC-035**: empty tier list raises `ValueError`;
  - **AC-036**: non-`Limit` entry in `Tier.limits` raises `TypeError`.
- [ ] T007 Create `tests/conftest.py` with:
  - a `FakeClock` with a settable `t` (int or Fraction) and a `now()` method;
  - a `fake_clock` fixture;
  - the example tier fixtures `free` (Limit(5, 1)), `pro` (Limit(20, 10)) and `layered` (Limit(5, 5), Limit(10, Fraction(1, 6))), taken from spec.md User Scenarios.
- [ ] T008 [P] Create `.harness/gates.sh`, a bash library of functions `gate_g1` … `gate_g6`. Each takes a root directory, runs inside it, prints `PASS/FAIL Gn` and returns non-zero on failure:
  - `gate_g1` integrity: fails if `git diff --name-only harness-approved..HEAD -- tests .harness` is non-empty; passes with a warning if the tag does not exist yet;
  - `gate_g2` suppressions: `rg --glob '*.py' --glob '!.venv/**' -e '#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no\s*cover|fmt:\s*off)'`, failing on any match;
  - `gate_g3` lint: `ruff check src tests` and `ruff format --check src tests`;
  - `gate_g4` security: `bandit -r src`;
  - `gate_g5` tests and coverage: `coverage run --branch -m pytest`, then `coverage report --fail-under=90`; prints the wall time;
  - `gate_g6` secrets: `detect-secrets scan` over the working tree, failing if `results` is not empty.
- [ ] T009 [P] Create `.harness/self_check.sh` (gate G7). It sources `gates.sh`, builds one deliberately broken fake per gate in a `mktemp -d` directory (never committed), runs that gate against it, and fails unless every gate fails on its fake:
  - G1: a throwaway `git init` repository tagged `harness-approved`, then a committed edit under `tests/`;
  - G2: a `*.py` file with a `# noqa` comment;
  - G3: a `src/` module with an unused import;
  - G4: a `src/` module that calls `eval` on input;
  - G5: a package with one failing test, and a second package whose tests leave branch coverage below 90 %;
  - G6: a text file holding a fake AWS-style access key. Build the key by string concatenation in the script, so G6 does not flag `self_check.sh` itself.
- [ ] T010 Create `.harness/run.sh`, which sources `gates.sh`, runs G1–G6 on the repository root and then `self_check.sh` (G7). It prints `PASS/FAIL Gn` for each gate and `ALL GATES PASSED`, and exits non-zero on the first failure.

**Checkpoint**: `.harness/self_check.sh` passes when run on its own (every gate fails on its fake). `.harness/run.sh` runs and stops at G5, because no tests exist yet.

---

## Phase 3: Protected Tests — all stories (RED) 🔒

**Purpose**: Encode every AC as a failing test. Every test function has `@pytest.mark.ac("AC-nnn", ...)`.

### User Story 1 tests (P1)

- [ ] T011 [P] [US1] Write tests for AC-001 to AC-007 in `tests/test_us1_token_bucket.py`, using `fake_clock` and the `free` tier. Times are exact `Fraction` values (e.g. `Fraction("0.999")`), never floats.

### User Story 2 tests (P1)

- [ ] T012 [P] [US2] Write tests for AC-008 to AC-011 and AC-027 in `tests/test_us2_tiers.py`. Use the `layered` tier and the exact t = 0/1/2 sequence from AC-009, and assert `inspect` returns `(5, Fraction(1, 3))` and leaves the state unchanged.

### User Story 3 tests (P1)

- [ ] T013 [P] [US3] Write tests for AC-012 to AC-017 in `tests/test_us3_http_mapping.py`:
  - use `Decision` values with `retry_after` set to `1`, `Fraction(3, 4)`, `2`, `Fraction(20001, 10000)` and `Fraction(1, 1000)`;
  - check that `Retry-After` matches `^[0-9]+$`;
  - for AC-016, retry exactly N seconds after the denial;
  - for AC-015, use the AC-009 sequence and expect `"4"`.

### User Story 4 tests (P2)

- [ ] T014 [P] [US4] Write tests for AC-018 to AC-024, AC-028 to AC-031, AC-035 and AC-036 in `tests/test_us4_validation.py`. Parametrise over the invalid values in spec.md, and check:
  - the exception type (`TypeError` vs `ValueError` vs `UnknownTierError` / `CostExceedsCapacityError`), following contracts/public-api.md §Errors;
  - that the message starts with the field name;
  - that `inspect` shows no tokens were taken.

### User Story 5 tests (P2) and cross-cutting

- [ ] T015 [P] [US5] Write tests for AC-025, AC-026, AC-032 and AC-034 in `tests/test_us5_determinism.py`:
  - a seeded `random.Random(2026)` scripted generator for 1,000 inputs (AC-025). The test loops 100 times, running the sequence on a fresh limiter each time, and asserts that all 100 decision sequences and their `repr()` bytes are identical (also backs SC-003);
  - 10,000 inputs across 100 clients for AC-034: for every client, every limit and every pair of accepted requests at t_i ≤ t_j, assert the cost accepted in [t_i, t_j] is at most capacity + rate × (t_j − t_i), in exact `Fraction` arithmetic;
  - `monkeypatch` making `time.time`, `time.monotonic`, `time.monotonic_ns` and `datetime.datetime.now` raise, for AC-026 and AC-032.
- [ ] T016 [P] [US5] Write a test for AC-033 in `tests/test_public_api.py`. It asserts `set(tiered_limiter.__all__)` equals the 11 names in plan.md §Public API (the same set as contracts/public-api.md).
- [ ] T017 Run `pytest` and confirm that **every** test fails (or errors on import) and none passes. Paste the failure counts into the commit message. Then check traceability by hand (constitution III, review): every `**AC-nnn**` in spec.md appears in at least one `pytest.mark.ac(...)`, every test function has a marker, and no marker cites an unknown AC. `rg -o 'AC-[0-9]{3}'` over spec.md and `tests/` gives the two lists to compare.

---

## Phase 4: Human Approval Gate 🔒

- [ ] T018 Commit `tests/`, `.harness/`, `pyproject.toml` and `requirements-dev.txt`.
- [ ] T019 **Human** reviews and approves the tests and the harness, including the T017 traceability check, then creates the tag: `git tag harness-approved`. From this point on, `tests/` and `.harness/` are read-only for the implementing agent.

**Checkpoint**: No source task (T020 onwards) starts until the tag exists.

---

## Phase 5: User Story 1 - Limit a client with a token bucket (Priority: P1) 🎯 MVP

**Goal**: Single-limit token bucket with continuous refill, a capacity cap and clock-backwards safety.

**Independent Test**: `pytest tests/test_us1_token_bucket.py`

- [ ] T020 [P] [US1] Implement the `Clock` protocol and `MonotonicClock` in `src/tiered_limiter/clock.py`, following research.md R2. It is the only module that imports `time`, and `MonotonicClock.now` returns the reading as a `Fraction`, never a `float`.
- [ ] T021 [P] [US1] Implement the validators in `src/tiered_limiter/_validate.py`: `require_int(field, value)`, `require_rational(field, value)`, `require_positive(field, value)`, `require_nonempty_str(field, value)`. Each one excludes `bool`, and error messages start with `"<field>: "`, following research.md R6.
- [ ] T022 [P] [US1] Implement `UnknownTierError` and `CostExceedsCapacityError`, both subclasses of `ValueError`, in `src/tiered_limiter/errors.py`.
- [ ] T023 [US1] Implement `Limit` in `src/tiered_limiter/config.py` as a frozen dataclass that validates in `__post_init__`. It covers `data-model.md Limit.capacity` and `data-model.md Limit.refill_rate`. Depends on T021.
- [ ] T024 [US1] Implement `BucketState` and the pure functions `refill`, `consume` and `wait_for` in `src/tiered_limiter/bucket.py`, following the data-model.md BucketState state transitions. They cover `data-model.md BucketState.balance` and `data-model.md BucketState.last_seen`.
- [ ] T025 [US1] Implement `Decision`, plus `TieredLimiter.__init__` and `acquire` for single-limit tiers, in `src/tiered_limiter/limiter.py`. This includes:
  - lazy full state keyed by `(client_key, tier_name)`, following research.md R5;
  - one `clock.now()` read per call;
  - validation of `data-model.md` Request inputs `cost` and `clock reading`;
  - `data-model.md Decision.retry_after`.

  Depends on T020, T023 and T024.

**Checkpoint (observe only, no fixes before impl-baseline)**: Record the pass/fail count of `pytest tests/test_us1_token_bucket.py`.

---

## Phase 6: User Story 2 - Tiers and layered limits (Priority: P1)

**Goal**: Named tiers, all-or-nothing multi-limit decisions, longest wait, read-only inspection.

**Independent Test**: `pytest tests/test_us2_tiers.py`

- [ ] T026 [US2] Implement `Tier` and `LimiterConfig` in `src/tiered_limiter/config.py`. They cover `data-model.md Tier.name`, `data-model.md Tier.limits` and `data-model.md LimiterConfig.tiers`, including the unique-name check. Depends on T023.
- [ ] T027 [US2] Extend `TieredLimiter.acquire` in `src/tiered_limiter/limiter.py` to layered limits, following research.md R4. It refills all limits, then either allows and consumes from all of them, or denies, consumes nothing, and sets `retry_after = max` over the blocking limits. It raises `UnknownTierError`, covering `data-model.md` Request inputs `tier_name`.
- [ ] T028 [US2] Implement `TieredLimiter.inspect` in `src/tiered_limiter/limiter.py`. It covers FR-015: it computes refill at `clock.now()` without storing it, never creates state, and returns full capacities for a client it has not seen.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us2_tiers.py`.

---

## Phase 7: User Story 3 - HTTP mapping (Priority: P1)

**Goal**: A decision becomes 200, or 429 with `Retry-After`.

**Independent Test**: `pytest tests/test_us3_http_mapping.py`

- [ ] T029 [P] [US3] Implement `HttpOutcome` and `to_http` in `src/tiered_limiter/http_mapping.py`, following research.md R7. They cover `data-model.md HttpOutcome.status` and `data-model.md HttpOutcome.headers`, using `max(1, math.ceil(retry_after))`.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us3_http_mapping.py`.

---

## Phase 8: User Story 4 - Reject invalid configuration (Priority: P2)

**Goal**: Every invalid input is rejected before any state changes, with an error that names the field.

**Independent Test**: `pytest tests/test_us4_validation.py`

- [ ] T030 [US4] Complete input validation at the start of `TieredLimiter.acquire` and `inspect` in `src/tiered_limiter/limiter.py`. Validate `data-model.md` Request inputs `client_key`, `tier_name` and `cost`, including the `CostExceedsCapacityError` check against every limit, before any state is read or written.
- [ ] T031 [US4] Make `src/tiered_limiter/config.py` reject a `Tier.limits` item that is not a `Limit` (AC-036, `TypeError`), and an empty `LimiterConfig.tiers` (AC-035, `ValueError`), as `data-model.md Tier.limits` and `data-model.md LimiterConfig.tiers` define. Check the error type and message prefix against contracts/public-api.md §Errors.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us4_validation.py`.

---

## Phase 9: User Story 5 - Determinism and public API (Priority: P2)

**Goal**: The same inputs give the same decisions, the system clock is never read, and the public API is exactly as planned.

**Independent Test**: `pytest tests/test_us5_determinism.py tests/test_public_api.py`

- [ ] T032 [US5] Populate `__all__` and the re-exports in `src/tiered_limiter/__init__.py` with exactly the 11 names in plan.md §Public API. Add the module docstring, which must say "not thread-safe" (FR-012).

**Checkpoint (observe only)**: Record the pass/fail count of the US5 tests.

---

## Phase 10: Baseline, Harness and Bounded Repair

**Purpose**: Constitution X.

- [ ] T033 Commit the whole first implementation unchanged, with message `impl: first generated implementation`, then run `git tag impl-baseline`.
- [ ] T034 Run `.harness/run.sh`, save the full output to `specs/001-tiered-rate-limiter/harness-run-0.log` and commit it.
- [ ] T035 If the harness is red: make repair attempt 1, changing only files under `src/`. Commit with subject `repair(1/2): <gate>: <summary>`, then re-run and log to `harness-run-1.log`.
- [ ] T036 If it is still red: make repair attempt 2, committed as `repair(2/2): …`, and log to `harness-run-2.log`. If it is still red after that, **stop** and open a human review that lists the failing gates. No third repair is allowed.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [ ] T037 [P] Write `README.md` covering installation, the quickstart example, the not-thread-safe warning and the exact-numbers rule (`int` / `Fraction` only). Link to contracts/public-api.md.
- [ ] T038 [P] Create `CLAUDE.md` (under 200 lines, as organisation policy requires) with the build, test and harness commands, the module map from plan.md, and the conventions: AC markers, protected paths, repair rules.
- [ ] T039 Run the quickstart.md smoke scenario by hand, then do a final `.harness/run.sh` and confirm `ALL GATES PASSED`. Then work through the constitution v1.0.2 Governance review checklist (imports, traceability, clock use, function length, change notes, repair count, suite time, `float` use) and record the result in the commit message.

---

## Dependencies & Execution Order

```text
Phase 1 Setup ─► Phase 2 Foundational ─► Phase 3 RED tests (all stories)
   ─► Phase 4 human approval (tag harness-approved)
   ─► Phase 5 US1 ─► Phase 6 US2 ─┬─► Phase 8 US4
                  └► Phase 7 US3  └─► Phase 9 US5
   ─► Phase 10 impl-baseline ─► harness ─► ≤ 2 repairs ─► Phase 11 Polish
```

- **US1** is the base for every other story (Clock, validators, Limit, bucket, limiter).
- **US2** depends on US1 (it extends `acquire` and `config.py`).
- **US3** depends only on `Decision` (T025). It can run in parallel with US2.
- **US4** depends on US2, because it validates `tier_name` against tiers and cost against all
  limits.
- **US5** depends on every export existing (US1–US4).
- `run.sh` (T010) depends on `gates.sh` (T008) and `self_check.sh` (T009).
- No harness-driven fixes are made before T033. The checkpoints only record results.

## Parallel Examples

```text
Phase 2:  T008 gates.sh, T009 self_check.sh, then T010 run.sh
Phase 3:  T011, T012, T013, T014, T015, T016 (separate test files)
US1:      T020 clock.py, T021 _validate.py, T022 errors.py, then T023 → T024 → T025
US2/US3:  T029 http_mapping.py runs in parallel with T026–T028
Polish:   T037 README.md, T038 CLAUDE.md
```

## Implementation Strategy

- **MVP = US1 + US2 + US3** (all P1). Together they deliver the stated product: a tiered limiter
  plus the 200/429 mapping. Constitution X still treats the whole of Phases 5–9 as one "first
  generated implementation", so the MVP is a review milestone, not a separate baseline.
- **Increment 2 = US4 + US5**: validation and determinism.
- **Repair budget**: 2 attempts in total across all gates (T035 and T036), then human review.

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude): applied `/speckit-analyze` fixes. Reason: align
  the tasks with the analysis findings, plan.md and constitution v1.0.1. Changes: T002 adds
  `tests/ruff.toml` (D1); T008 matches only comment syntax in `*.py` files (D2); T015 G11 scans
  every commit and fails on zero files (U1); T006 marked done with AC-033 to AC-036, and T019,
  T020 and T036 cite them (C1, C2, A1); T020 loops the determinism run 100 times (I1); new T044
  adds the SC-004 README example and line-count check, and the old T044 and T045 become T045 and
  T046 (C3). Affected: AC-025, AC-033, AC-034, AC-035, AC-036. (Task IDs in this entry refer to
  the numbering before the lean-scope entry below.)
- **2026-11-22** (Deepanshi Bansal, with Claude): lean-scope update to match constitution v1.0.2
  and plan.md §Harness Gates. Reason: one-day deadline. Removed: the `bench/` tasks (SC-005
  benchmark, SC-004 README example and line-count check), the reverse-order hook, the history
  secret scan, the checksum manifest, mypy and pip-audit, and the clock-purity, function-size,
  traceability, dependency and repair-budget gate scripts. Added: `.harness/gates.sh` (G1–G6),
  `.harness/self_check.sh` (G7, broken fakes) and a manual traceability check at T017 plus the
  review checklist at T039. T016 and T032 use plan.md §Public API (analysis finding C1). Tasks
  renumbered T001–T039. Every FR, SC and AC is unchanged. No AC IDs are affected.
