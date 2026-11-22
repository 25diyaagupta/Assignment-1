---

description: "Task list for the Tiered Token-Bucket Rate Limiter"
---

# Tasks: Tiered Token-Bucket Rate Limiter

**Input**: Design documents from `specs/001-tiered-rate-limiter/`

**Prerequisites**: plan.md, spec.md (Approved), research.md, data-model.md,
contracts/public-api.md, quickstart.md

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

- [ ] T001 Create `.venv` with `python3.12 -m venv .venv`. Resolve the current versions of pytest, coverage, ruff, bandit, mypy, pip-audit and detect-secrets at the registry, then write exact `==` pins to `requirements-dev.txt`. Use only the packages in the plan.md §Dependency Justification table.
- [ ] T002 Create `pyproject.toml` with:
  - project `tiered-limiter` using the `src` layout, `requires-python = ">=3.12,<3.13"` and no runtime dependencies;
  - `[tool.ruff]` with target `py312` and `select` rules E, F, W, I, B, C90, D, ANN, S, UP, SIM, PL, with `max-complexity = 10` and pydocstyle `convention = "google"`. Add no `ignore`, `extend-ignore` or `per-file-ignores` entries;
  - `[tool.mypy] strict = true`;
  - `[tool.coverage]` with `branch = true`, `source = ["src"]`, `fail_under = 90` and no omit entries;
  - `[tool.pytest.ini_options]` that registers the `ac` marker and sets `--strict-markers`.

  Also create `tests/ruff.toml` with `extend = "../pyproject.toml"` and a `[lint]` `select` of E, F, W, I, B, C90, UP, SIM only, as plan.md §Ruff Rule Sets records (constitution II, v1.0.1). It has no `ignore`, `extend-ignore`, `per-file-ignores` or `exclude` entries.
- [ ] T003 [P] Create the package skeleton `src/tiered_limiter/__init__.py` with a module docstring and `__all__: list[str] = []`. No exports yet, so the tests fail on import.
- [ ] T004 [P] Add the virtual environment, cache and coverage entries (`.venv/`, `__pycache__/`, `.coverage`, `.mypy_cache/`, `.ruff_cache/`, `.pytest_cache/`) to `.gitignore`.
- [ ] T005 Install the tools: `pip install -r requirements-dev.txt && pip install -e .`. Record the `pip freeze` output in the commit message, and confirm that `ruff check .` and `mypy --strict src` pass on the skeleton.

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
  - the example tier fixtures `free` (Limit(5, 1)), `pro` (Limit(20, 10)) and `layered` (Limit(5, 5), Limit(10, Fraction(1, 6))), taken from spec.md User Scenarios;
  - a `pytest_collection_modifyitems` hook that reverses item order when the environment variable `HARNESS_REVERSE=1` is set.
- [ ] T008 [P] Create `.harness/check_suppressions.sh` (gate G2). It:
  - runs `rg --glob '*.py' -e '#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no\s*cover|fmt:\s*(off|skip))'` across the repository, excluding `.venv/`. It matches only comment syntax in `*.py` files, so documentation and this script do not match;
  - runs `rg -e '^\s*(ignore|extend-ignore|per-file-ignores|skips|omit|exclude)\s*='` over `pyproject.toml` and `tests/ruff.toml`;
  - exits 1 on any match.
- [ ] T009 [P] Create `.harness/check_clock_purity.py` (gate G6). It is an AST scan of `src/` that fails on:
  - any `import time`, `from time`, `datetime` or `random` outside `src/tiered_limiter/clock.py`;
  - any use of the name `float` anywhere in `src/`.
- [ ] T010 [P] Create `.harness/check_function_size.py` (gate G7). It is an AST scan of `src/`, `.harness/` and `tests/` that fails when any function has `end_lineno - lineno + 1 > 40`. It prints `file:line name length`.
- [ ] T011 [P] Create `.harness/check_traceability.py` (gate G8). It parses the `**AC-nnn**` IDs from `specs/001-tiered-rate-limiter/spec.md` and the `pytest.mark.ac(...)` arguments from `tests/` using AST. It fails on:
  - ACs with no test;
  - test functions with no `ac` marker;
  - markers that cite unknown ACs.
- [ ] T012 [P] Create `.harness/check_dependencies.py` (gate G12, part 1). It fails if any package in `requirements-dev.txt` is not pinned with `==`, or is missing from the plan.md §Dependency Justification table.
- [ ] T013 [P] Create `.harness/check_repair_budget.sh` (gate G13). If tag `impl-baseline` exists, it counts commits after it whose subject starts with `repair(` and fails if there are more than 2.
- [ ] T014 [P] Create `.harness/check_protection.sh` (gate G1). It fails if `git diff --name-only harness-approved..HEAD -- tests .harness` is non-empty, or if `sha256sum -c .harness/MANIFEST.sha256` fails. It passes with a warning before the tag exists.
- [ ] T015 Create `.harness/run.sh`, which runs G1–G13 in order (the constitution's Quality Gates table):
  - G1 protection;
  - G2 suppressions;
  - G3 `ruff check .` and `ruff format --check .` (ruff applies `tests/ruff.toml` to `tests/` and `pyproject.toml` elsewhere);
  - G4 `bandit -r src`;
  - G5 `mypy --strict src`;
  - G6 clock purity;
  - G7 function size, plus ruff C901;
  - G8 traceability;
  - G9 pytest in normal order and with `HARNESS_REVERSE=1`, each under 10 s;
  - G10 `coverage run --branch -m pytest` and `coverage report --fail-under=90`;
  - G11 `detect-secrets scan` over the working tree, then a history scan of **every** commit in `git rev-list --all`: for each commit, `git archive <sha> | tar -x -C <tmpdir>`, run `detect-secrets scan --all-files <tmpdir>`, and add the commit's file count (`git ls-tree -r --name-only <sha> | wc -l`) to a running total. It fails on any finding, and fails if the history scan covered zero commits or zero files. It prints the commit and file totals;
  - G12 dependencies plus `pip-audit -r requirements-dev.txt`;
  - G13 repair budget.

  It prints `PASS/FAIL Gn` for each gate and `ALL GATES PASSED`, and exits non-zero on the first failure.

**Checkpoint**: The harness runs. G9 and G10 fail because no tests exist yet.

---

## Phase 3: Protected Tests — all stories (RED) 🔒

**Purpose**: Encode every AC as a failing test. Every test function has `@pytest.mark.ac("AC-nnn", ...)`.

### User Story 1 tests (P1)

- [ ] T016 [P] [US1] Write tests for AC-001 to AC-007 in `tests/test_us1_token_bucket.py`, using `fake_clock` and the `free` tier. Times are exact `Fraction` values (e.g. `Fraction("0.999")`), never floats.

### User Story 2 tests (P1)

- [ ] T017 [P] [US2] Write tests for AC-008 to AC-011 and AC-027 in `tests/test_us2_tiers.py`. Use the `layered` tier and the exact t = 0/1/2 sequence from AC-009, and assert `inspect` returns `(5, Fraction(1, 3))` and leaves the state unchanged.

### User Story 3 tests (P1)

- [ ] T018 [P] [US3] Write tests for AC-012 to AC-017 in `tests/test_us3_http_mapping.py`:
  - use `Decision` values with `retry_after` set to `1`, `Fraction(3, 4)`, `2`, `Fraction(20001, 10000)` and `Fraction(1, 1000)`;
  - check that `Retry-After` matches `^[0-9]+$`;
  - for AC-016, retry exactly N seconds after the denial;
  - for AC-015, use the AC-009 sequence and expect `"4"`.

### User Story 4 tests (P2)

- [ ] T019 [P] [US4] Write tests for AC-018 to AC-024, AC-028 to AC-031, AC-035 and AC-036 in `tests/test_us4_validation.py`. Parametrise over the invalid values in spec.md, and check:
  - the exception type (`TypeError` vs `ValueError` vs `UnknownTierError` / `CostExceedsCapacityError`), following contracts/public-api.md §Errors;
  - that the message starts with the field name;
  - that `inspect` shows no tokens were taken.

### User Story 5 tests (P2) and cross-cutting

- [ ] T020 [P] [US5] Write tests for AC-025, AC-026, AC-032 and AC-034 in `tests/test_us5_determinism.py`:
  - a seeded `random.Random(2026)` scripted generator for 1,000 inputs (AC-025). The test loops 100 times, running the sequence on a fresh limiter each time, and asserts that all 100 decision sequences and their `repr()` bytes are identical (also backs SC-003);
  - 10,000 inputs across 100 clients for AC-034: for every client, every limit and every pair of accepted requests at t_i ≤ t_j, assert the cost accepted in [t_i, t_j] is at most capacity + rate × (t_j − t_i), in exact `Fraction` arithmetic;
  - `monkeypatch` making `time.time`, `time.monotonic`, `time.monotonic_ns` and `datetime.datetime.now` raise, for AC-026 and AC-032.
- [ ] T021 [P] [US5] Write a test for AC-033 in `tests/test_public_api.py`. It asserts `set(tiered_limiter.__all__)` equals the 11 names in contracts/public-api.md.
- [ ] T022 Run `pytest` and confirm that **every** test fails (or errors on import) and none passes. Paste the failure counts into the commit message. Then run `.harness/check_traceability.py` and confirm it reports zero orphans.

---

## Phase 4: Human Approval Gate 🔒

- [ ] T023 Generate `.harness/MANIFEST.sha256` with `sha256sum` over every file in `tests/` and `.harness/` except the manifest itself. Commit `tests/`, `.harness/`, `pyproject.toml` and `requirements-dev.txt`.
- [ ] T024 **Human** reviews and approves the tests and the harness, then creates the tag: `git tag harness-approved`. From this point on, `tests/` and `.harness/` are read-only for the implementing agent.

**Checkpoint**: No source task (T025 onwards) starts until the tag exists.

---

## Phase 5: User Story 1 - Limit a client with a token bucket (Priority: P1) 🎯 MVP

**Goal**: Single-limit token bucket with continuous refill, a capacity cap and clock-backwards safety.

**Independent Test**: `pytest tests/test_us1_token_bucket.py`

- [ ] T025 [P] [US1] Implement the `Clock` protocol and `MonotonicClock` in `src/tiered_limiter/clock.py`, following research.md R2. It is the only module that imports `time`, and `MonotonicClock.now` returns the reading as a `Fraction`, never a `float`.
- [ ] T026 [P] [US1] Implement the validators in `src/tiered_limiter/_validate.py`: `require_int(field, value)`, `require_rational(field, value)`, `require_positive(field, value)`, `require_nonempty_str(field, value)`. Each one excludes `bool`, and error messages start with `"<field>: "`, following research.md R6.
- [ ] T027 [P] [US1] Implement `UnknownTierError` and `CostExceedsCapacityError`, both subclasses of `ValueError`, in `src/tiered_limiter/errors.py`.
- [ ] T028 [US1] Implement `Limit` in `src/tiered_limiter/config.py` as a frozen dataclass that validates in `__post_init__`. It covers `data-model.md Limit.capacity` and `data-model.md Limit.refill_rate`. Depends on T026.
- [ ] T029 [US1] Implement `BucketState` and the pure functions `refill`, `consume` and `wait_for` in `src/tiered_limiter/bucket.py`, following the data-model.md BucketState state transitions. They cover `data-model.md BucketState.balance` and `data-model.md BucketState.last_seen`.
- [ ] T030 [US1] Implement `Decision`, plus `TieredLimiter.__init__` and `acquire` for single-limit tiers, in `src/tiered_limiter/limiter.py`. This includes:
  - lazy full state keyed by `(client_key, tier_name)`, following research.md R5;
  - one `clock.now()` read per call;
  - validation of `data-model.md` Request inputs `cost` and `clock reading`;
  - `data-model.md Decision.retry_after`.

  Depends on T025, T028 and T029.

**Checkpoint (observe only, no fixes before impl-baseline)**: Record the pass/fail count of `pytest tests/test_us1_token_bucket.py`.

---

## Phase 6: User Story 2 - Tiers and layered limits (Priority: P1)

**Goal**: Named tiers, all-or-nothing multi-limit decisions, longest wait, read-only inspection.

**Independent Test**: `pytest tests/test_us2_tiers.py`

- [ ] T031 [US2] Implement `Tier` and `LimiterConfig` in `src/tiered_limiter/config.py`. They cover `data-model.md Tier.name`, `data-model.md Tier.limits` and `data-model.md LimiterConfig.tiers`, including the unique-name check. Depends on T028.
- [ ] T032 [US2] Extend `TieredLimiter.acquire` in `src/tiered_limiter/limiter.py` to layered limits, following research.md R4. It refills all limits, then either allows and consumes from all of them, or denies, consumes nothing, and sets `retry_after = max` over the blocking limits. It raises `UnknownTierError`, covering `data-model.md` Request inputs `tier_name`.
- [ ] T033 [US2] Implement `TieredLimiter.inspect` in `src/tiered_limiter/limiter.py`. It covers FR-015: it computes refill at `clock.now()` without storing it, never creates state, and returns full capacities for a client it has not seen.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us2_tiers.py`.

---

## Phase 7: User Story 3 - HTTP mapping (Priority: P1)

**Goal**: A decision becomes 200, or 429 with `Retry-After`.

**Independent Test**: `pytest tests/test_us3_http_mapping.py`

- [ ] T034 [P] [US3] Implement `HttpOutcome` and `to_http` in `src/tiered_limiter/http_mapping.py`, following research.md R7. They cover `data-model.md HttpOutcome.status` and `data-model.md HttpOutcome.headers`, using `max(1, math.ceil(retry_after))`.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us3_http_mapping.py`.

---

## Phase 8: User Story 4 - Reject invalid configuration (Priority: P2)

**Goal**: Every invalid input is rejected before any state changes, with an error that names the field.

**Independent Test**: `pytest tests/test_us4_validation.py`

- [ ] T035 [US4] Complete input validation at the start of `TieredLimiter.acquire` and `inspect` in `src/tiered_limiter/limiter.py`. Validate `data-model.md` Request inputs `client_key`, `tier_name` and `cost`, including the `CostExceedsCapacityError` check against every limit, before any state is read or written.
- [ ] T036 [US4] Make `src/tiered_limiter/config.py` reject a `Tier.limits` item that is not a `Limit` (AC-036, `TypeError`), and an empty `LimiterConfig.tiers` (AC-035, `ValueError`), as `data-model.md Tier.limits` and `data-model.md LimiterConfig.tiers` define. Check the error type and message prefix against contracts/public-api.md §Errors.

**Checkpoint (observe only)**: Record the pass/fail count of `pytest tests/test_us4_validation.py`.

---

## Phase 9: User Story 5 - Determinism and public API (Priority: P2)

**Goal**: The same inputs give the same decisions, the system clock is never read, and the public API is exactly as contracted.

**Independent Test**: `pytest tests/test_us5_determinism.py tests/test_public_api.py`

- [ ] T037 [US5] Populate `__all__` and the re-exports in `src/tiered_limiter/__init__.py` with exactly the 11 names in contracts/public-api.md. Add the module docstring, which must say "not thread-safe" (FR-012).
- [ ] T038 [P] [US5] Create `bench/bench_decisions.py`, which reports the time for 100,000 decisions across 10,000 clients (SC-005). It is not gated, is not a test, and uses `MonotonicClock`.

**Checkpoint (observe only)**: Record the pass/fail count of the US5 tests.

---

## Phase 10: Baseline, Harness and Bounded Repair

**Purpose**: Constitution X.

- [ ] T039 Commit the whole first implementation unchanged, with message `impl: first generated implementation`, then run `git tag impl-baseline`.
- [ ] T040 Run `.harness/run.sh`, save the full output to `specs/001-tiered-rate-limiter/harness-run-0.log` and commit it.
- [ ] T041 If the harness is red: make repair attempt 1, changing only files under `src/`, `bench/` and `README.md`. Commit with subject `repair(1/2): <gate>: <summary>`, then re-run and log to `harness-run-1.log`.
- [ ] T042 If it is still red: make repair attempt 2, committed as `repair(2/2): …`, and log to `harness-run-2.log`. If it is still red after that, **stop** and open a human review that lists the failing gates. No third repair is allowed.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [ ] T043 [P] Write `README.md` covering installation, the quickstart example, the not-thread-safe warning and the exact-numbers rule (`int` / `Fraction` only). Link to contracts/public-api.md.
- [ ] T044 Add the SC-004 example to `README.md`, between `<!-- SC-004:begin -->` and `<!-- SC-004:end -->`: a fenced Python block that defines a new tier, builds a `TieredLimiter`, decides one request and maps it with `to_http`. Create `bench/check_readme_example.py`, which extracts that block, counts its non-blank, non-comment lines (imports included), exits 1 if the count is above 10 or the block is missing, then runs the block and exits 1 if it raises. It prints `SC-004: <n> lines`. It is not a test and not a gate. Depends on T043.
- [ ] T045 [P] Create `CLAUDE.md` (under 200 lines, as organisation policy requires) with the build, test and harness commands, the module map from plan.md, and the conventions: AC markers, protected paths, repair rules.
- [ ] T046 Run the quickstart.md smoke scenario by hand and `python bench/check_readme_example.py`, then do a final `.harness/run.sh` and confirm `ALL GATES PASSED`.

---

## Dependencies & Execution Order

```text
Phase 1 Setup ─► Phase 2 Foundational (T006 spec amendment first) ─► Phase 3 RED tests (all stories)
   ─► Phase 4 human approval (tag harness-approved)
   ─► Phase 5 US1 ─► Phase 6 US2 ─┬─► Phase 8 US4
                  └► Phase 7 US3  └─► Phase 9 US5
   ─► Phase 10 impl-baseline ─► harness ─► ≤ 2 repairs ─► Phase 11 Polish
```

- **US1** is the base for every other story (Clock, validators, Limit, bucket, limiter).
- **US2** depends on US1 (it extends `acquire` and `config.py`).
- **US3** depends only on `Decision` (T030). It can run in parallel with US2.
- **US4** depends on US2, because it validates `tier_name` against tiers and cost against all
  limits.
- **US5** depends on every export existing (US1–US4).
- No harness-driven fixes are made before T039. The checkpoints only record results.

## Parallel Examples

```text
Phase 2:  T008, T009, T010, T011, T012, T013, T014 (separate .harness files)
Phase 3:  T016, T017, T018, T019, T020, T021 (separate test files)
US1:      T025 clock.py, T026 _validate.py, T027 errors.py, then T028 → T029 → T030
US2/US3:  T034 http_mapping.py runs in parallel with T031–T033
Polish:   T043 README.md, T045 CLAUDE.md, then T044 after T043
```

## Implementation Strategy

- **MVP = US1 + US2 + US3** (all P1). Together they deliver the stated product: a tiered limiter
  plus the 200/429 mapping. Constitution X still treats the whole of Phases 5–9 as one "first
  generated implementation", so the MVP is a review milestone, not a separate baseline.
- **Increment 2 = US4 + US5**: validation and determinism.
- **Repair budget**: 2 attempts in total across all gates (T041 and T042), then human review.

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude): applied `/speckit-analyze` fixes. Reason: align
  the tasks with the analysis findings, plan.md and constitution v1.0.1. Changes: T002 adds
  `tests/ruff.toml` (D1); T008 matches only comment syntax in `*.py` files (D2); T015 G11 scans
  every commit and fails on zero files (U1); T006 marked done with AC-033 to AC-036, and T019,
  T020 and T036 cite them (C1, C2, A1); T020 loops the determinism run 100 times (I1); new T044
  adds the SC-004 README example and line-count check, and the old T044 and T045 become T045 and
  T046 (C3). Affected: AC-025, AC-033, AC-034, AC-035, AC-036.
