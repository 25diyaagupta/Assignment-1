<!--
Sync Impact Report
- Version change: 1.0.2 → 1.0.3 (PATCH: scope of the VII secret scan narrowed)
- Modified principles: VII (secret scan limited to project files)
- Modified sections: Quality Gates (G6 row)
- Added principles: none
- Removed principles: none
- Templates requiring updates: none; plan.md and tasks.md of 001-tiered-rate-limiter updated
  to match (✅)
- Deferred TODOs: none
- Previous: 1.0.1 → 1.0.2 (lean scope: 7 gates, review checklist); 1.0.0 → 1.0.1 (II: ruff scope split for tests/); (template) → 1.0.0, initial
  ratification with principles I–XVI
-->

# Tiered Token-Bucket Rate Limiter Constitution

Scope: a Python library implementing a tiered token-bucket rate limiter, plus a function that maps
a limiter result to an HTTP outcome (200, or 429 with a `Retry-After` header).

Every principle below is phrased so that a tool, script or `git` query can return pass/fail.
"Harness" means the gate scripts under `.harness/`, run by one command that exits 0 only when all
gates pass. A check marked **(review)** is run by the human reviewer, using the checklist in
Governance, and is not a harness gate.

## Core Principles

### I. Python 3.12, Standard Library Core

- The package declares `requires-python = ">=3.12,<3.13"`; the harness runs on CPython 3.12.
- Modules in the core package import only the standard library and the package itself.
  Check (review): an import scan of `src/` finds no third-party top-level module.
- Every dependency beyond the standard library (including dev and test tools) is listed in
  `plan.md` with a one-line justification. Check (review): a dependency with no entry fails
  review.

### II. Zero Lint and Security Findings, No Suppressions

- `ruff check src tests` and `ruff format --check src tests` report zero findings. `src/` is
  checked with the full rule set in `pyproject.toml`. `tests/` is checked with a smaller rule
  set in `tests/ruff.toml` (its own `select` list), recorded with a justification for each
  omitted rule family in `plan.md`. Neither file has `ignore`, `extend-ignore`,
  `per-file-ignores` or `exclude` entries.
- `bandit -r src` reports zero findings at every severity and confidence level.
- No `*.py` file has a `noqa`, `nosec`, `type: ignore`, `pragma: no cover` or `fmt: off`
  comment. Check: `rg` over `*.py` files for that comment syntax returns no matches.

### III. Binary, Traceable Acceptance Criteria

- Every acceptance criterion has a unique ID `AC-nnn` (three digits) and a pass/fail outcome.
  Words like "fast", "robust" or "appropriate" with no threshold are not allowed.
- Every AC has at least one pytest test. Every test function names exactly the AC IDs it covers
  in its name or in a `@pytest.mark.ac("AC-nnn")` marker.
- Check (review): zero ACs with no test, zero tests with no AC, and zero references to AC IDs
  that do not exist in `spec.md`.

### IV. Injected Clock, Deterministic Behaviour

- Time reaches core logic only through a `Clock` protocol passed in by the caller.
  Only the one adapter module that provides the production clock may call `time.*`.
- Outside that adapter, `src/` contains no calls to `time.time`, `time.monotonic`,
  `time.perf_counter`, `time.sleep`, `datetime.now`, `datetime.utcnow` or `random`.
  Check (review): an `rg` scan of `src/` returns zero hits.
- Tests use a fake clock and never sleep. The same inputs and clock readings always give the
  same outputs.

### V. Small, Simple Functions

- No function or method is longer than 40 lines, counted from the `def` line to the last line of
  its body (AST `end_lineno - lineno + 1`), and that count includes docstrings.
- Cyclomatic complexity is at most 10 per function (ruff `C901`, `max-complexity = 10`).
- Check: ruff `C901` (gate G3) for complexity. Check (review): function length.

### VI. Branch Coverage ≥ 90 %

- `coverage run --branch -m pytest` followed by `coverage report --fail-under=90` passes over
  `src/`. Coverage omit lists may not include files from `src/`.

### VII. No Secrets in the Repository

- No keys, tokens, passwords or credentials are committed.
- Check: a secret scanner over the project files (`src/`, `tests/`, `.harness/` and the root config files `pyproject.toml`, `requirements-dev.txt` and `.gitignore`) reports zero findings, with
  every detector enabled and no suppressions, and Bandit's hard-coded-credential checks
  (B105–B107) report zero findings. Spec Kit tooling under `.specify/` and `.claude/` and the
  documentation under `specs/` are not scanned. Git history is not scanned.

### VIII. Protected, Pre-Approved Tests and Harness

- `tests/` and `.harness/` are written, reviewed and approved by a human before any
  implementation code exists. Approval is recorded as the git tag `harness-approved`.
- After that tag, the implementing agent must not add, edit, delete or weaken any file under
  `tests/` or `.harness/`. It must not lower thresholds, skip or xfail tests, or bypass a gate.
- Check: `git diff --name-only harness-approved..HEAD -- tests .harness` is empty for every
  implementation or repair commit.
- A change to protected files needs a human-approved specification change (Principle IX) and a
  new approval tag.

### IX. Specification Changes Only Through Spec Kit

- Requirements, ACs and design decisions change only in the Spec Kit artifacts
  (`spec.md`, `plan.md`, `tasks.md`, this constitution).
- Every change adds a dated entry (`YYYY-MM-DD`, author, reason, affected AC IDs) to the
  artifact's change-note section.
- Check: every commit that touches a Spec Kit artifact also adds a change-note entry.

### X. Baseline Preservation and Bounded Repair

- The first generated implementation is committed unchanged and tagged `impl-baseline`
  before any repair driven by the harness.
- At most 2 repair attempts are allowed, each one a separate commit with a message starting
  `repair(1/2):` or `repair(2/2):`.
- If the harness is still red after attempt 2, work stops and a human review is opened.
  Check (review): a third `repair` commit fails review.

### XI. Static Typing (additional)

- All public functions, methods and class attributes in `src/` have type annotations.
- Check: ruff `ANN` rules (gate G3). mypy is not run.

### XII. Hermetic, Fast, Order-Independent Tests (additional)

- Tests do no network I/O, write no files outside `tmp_path`, do not sleep and do not read the
  wall clock.
- Tests do not depend on each other's state.
- Full-suite wall time is under 10 seconds on the reference machine. This keeps the tests
  free of real time. Check (review): the time printed by gate G5.

### XIII. Explicit Error Contract (additional)

- Invalid configuration (non-positive capacity or refill rate, non-finite numbers, empty or
  duplicate tier list, non-positive token cost) raises `ValueError` or `TypeError` when it is
  constructed or called. It must never be silently clamped.
- Every such rejection has its own AC and test. Core logic never uses `assert` for runtime
  validation (Bandit B101).

### XIV. Documented Public API (additional)

- Every public module, class and function has a docstring (ruff `D` rules, Google convention).
- The public API is exactly the names in the package `__all__`. Check: a test compares
  `__all__` against the API list in `plan.md`.

### XV. Pinned, Audited Dependencies (additional)

- Dev and test tools are pinned to exact versions in one lock or requirements file.

### XVI. Numeric Determinism (additional)

- Token arithmetic gives the same results on every platform. Token counts and clock readings in
  core logic are typed `int` (fixed units) or `Fraction`, never `float`. Check (review): an `rg`
  scan for `float` in `src/` core modules. The representation is chosen in `plan.md`.
- `Retry-After` is a whole number of seconds ≥ 1, rounded up from the exact wait time. This is
  verified by ACs covering boundary values.

## Quality Gates (Harness)

The harness runs these gates in order, and each must pass for a change to be accepted:

| Gate | Command / check | Pass condition |
|------|-----------------|----------------|
| G1 Integrity | `git diff --name-only harness-approved..HEAD -- tests .harness` | empty diff |
| G2 Suppressions | `rg` for suppression comment syntax in `*.py` files | zero matches |
| G3 Lint/format | `ruff check src tests` and `ruff format --check src tests` | zero findings |
| G4 Security | `bandit -r src` | zero findings |
| G5 Tests and coverage | `coverage run --branch -m pytest`, then `coverage report --fail-under=90` | all tests pass, ≥ 90 % |
| G6 Secrets | `detect-secrets scan` over `src tests .harness` and the root config files | zero findings, at least one file scanned |
| G7 Self-check | G1–G6 run against deliberately broken fakes built in a temporary directory | every gate fails on its fake |

## Development Workflow

1. Run `/speckit-specify`, then `/speckit-clarify`, to produce `spec.md` with binary `AC-nnn`
   criteria.
2. Run `/speckit-plan` to produce `plan.md`: dependencies with justifications, Clock protocol,
   numeric representation, public API list. This step also runs the Constitution Check.
3. Run `/speckit-tasks`. Then write `tests/` and `.harness/`, get human approval, and tag
   `harness-approved`. At this point tests must fail (red).
4. Run `/speckit-implement`. Commit the first output unchanged and tag `impl-baseline`.
5. Run the harness. If it is red, make up to 2 `repair(n/2)` commits. If it is still red, a
   human reviews it.

## Governance

- This constitution overrides every other practice in the project. `/speckit-plan` and
  `/speckit-analyze` must check plans and tasks against it, and any violation is CRITICAL.
- Amendments are made only through `/speckit-constitution`. Each one carries a dated change note
  and a semantic version bump: MAJOR when a principle is removed or redefined, MINOR when a
  principle is added or materially expanded, PATCH when only the wording is clarified.
- No implementing agent may amend this constitution. Amendments need human approval.
- Every review checks that all harness gates are green and that Principles VIII and X hold.
- Every review also works through this checklist of **(review)** checks, which are not harness
  gates: no third-party imports in `src/` and every dependency justified (I); AC ↔ test
  traceability (III); no wall-clock or `random` use outside the clock adapter (IV); functions
  ≤ 40 lines (V); every commit touching a Spec Kit artifact adds a change note (IX); at most 2
  `repair` commits (X); suite time under 10 s (XII); no `float` in core modules (XVI).

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude), v1.0.0 → v1.0.1: Principle II now runs ruff
  with the full rule set on project code and a smaller, documented rule set on `tests/`
  (`/speckit-analyze` finding D1, option a). Reason: the full set includes rules that conflict
  with ordinary pytest code (`S101` flags every `assert`, `PLR2004` flags the literal expected
  values the ACs specify), and the no-suppression rule left no compliant way to write the tests.
  No AC IDs are affected.
- **2026-11-22** (Deepanshi Bansal, with Claude), v1.0.1 → v1.0.2: lean-scope amendment. The
  harness is cut to 7 gates: ruff (full set on `src/`, smaller documented set on `tests/`),
  bandit on `src/`, pytest with the coverage threshold, the suppression check (comment syntax in
  `*.py` only), a working-tree secret scan, an integrity diff against `harness-approved`, and a
  self-check on deliberately broken fakes. The checks in I, III, IV, V, X, XII and XVI move to
  human review. The history secret scan, the checksum manifest, mypy, pip-audit and the
  reverse-order run are removed. Reason: one-day deadline. No AC IDs are affected, and no
  requirement or AC in spec.md changes.
- **2026-11-22** (Deepanshi Bansal, with Claude), v1.0.2 → v1.0.3: Principle VII and the G6 row
  limit the secret scan to the project files: `src/`, `tests/`, `.harness/` and the root config
  files `pyproject.toml`, `requirements-dev.txt` and `.gitignore`. Every detector stays enabled
  and no suppression is added. Reason: Spec Kit's own `.specify/` files
  (`integrations/*.manifest.json`, `memory/.constitution-template.json`) contain SHA-256 hashes,
  which the hex high-entropy detector reports although they are not secrets; G6 could never
  pass on them. No AC IDs are affected.

**Version**: 1.0.3 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
