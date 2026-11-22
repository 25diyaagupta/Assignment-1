<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: all template placeholders replaced (initial ratification)
- Added principles: I–X (user-supplied), XI–XVI (additional measurable standards)
- Added sections: Quality Gates (harness), Development Workflow, Governance
- Removed sections: none
- Templates requiring updates: none modified by this command; plan-template "Constitution Check"
  reads this file at runtime (✅ no edit needed)
- Deferred TODOs: none
-->

# Tiered Token-Bucket Rate Limiter Constitution

Scope: a Python library implementing a tiered token-bucket rate limiter, plus a function that maps
a limiter result to an HTTP outcome (200, or 429 with a `Retry-After` header).

Every principle below is phrased so that a tool, script or `git` query can return pass/fail.
"Harness" means the gate scripts under `.harness/`, run by one command that exits 0 only when all
gates pass.

## Core Principles

### I. Python 3.12, Standard Library Core

- The package declares `requires-python = ">=3.12,<3.13"`; the harness runs on CPython 3.12.
- Modules in the core package import only the standard library and the package itself.
  Check: an import scan of `src/` finds no third-party top-level module.
- Every dependency beyond the standard library (including dev and test tools) is listed in
  `plan.md` with a one-line justification. A dependency with no entry fails the gate.

### II. Zero Lint and Security Findings, No Suppressions

- `ruff check .` and `ruff format --check .` report zero findings.
- `bandit -r src` reports zero findings at every severity and confidence level.
- The repository has no `noqa`, `nosec`, `type: ignore`, `pragma: no cover` or
  `# fmt: off` comments, and no `ignore`, `extend-ignore`, `per-file-ignores`, `skips` or
  `exclude` entries that switch off rules for project code. Check: `rg` over the repo and the tool
  config returns no matches.

### III. Binary, Traceable Acceptance Criteria

- Every acceptance criterion has a unique ID `AC-nnn` (three digits) and a pass/fail outcome.
  Words like "fast", "robust" or "appropriate" with no threshold are not allowed.
- Every AC has at least one pytest test. Every test function names exactly the AC IDs it covers
  in its name or in a `@pytest.mark.ac("AC-nnn")` marker.
- Check: a traceability script reports zero ACs with no test, zero tests with no AC, and zero
  references to AC IDs that do not exist in `spec.md`.

### IV. Injected Clock, Deterministic Behaviour

- Time reaches core logic only through a `Clock` protocol passed in by the caller.
  Only the one adapter module that provides the production clock may call `time.*`.
- Outside that adapter, `src/` contains no calls to `time.time`, `time.monotonic`,
  `time.perf_counter`, `time.sleep`, `datetime.now`, `datetime.utcnow` or `random`.
  Check: an AST or `rg` scan returns zero hits.
- Tests use a fake clock and never sleep. The same inputs and clock readings always give the
  same outputs.

### V. Small, Simple Functions

- No function or method is longer than 40 lines, counted from the `def` line to the last line of
  its body (AST `end_lineno - lineno + 1`), and that count includes docstrings.
- Cyclomatic complexity is at most 10 per function (ruff `C901`, `max-complexity = 10`).
- Check: ruff for complexity, plus a harness AST script for length (ruff has no line-length rule
  for functions).

### VI. Branch Coverage ≥ 90 %

- `coverage run --branch -m pytest` followed by `coverage report --fail-under=90` passes over
  `src/`. Coverage omit lists may not include files from `src/`.

### VII. No Secrets in the Repository

- No keys, tokens, passwords or credentials are committed, and none appear in git history.
- Check: a secret scanner over the working tree and full history reports zero findings, and
  Bandit's hard-coded-credential checks (B105–B107) report zero findings.

### VIII. Protected, Pre-Approved Tests and Harness

- `tests/` and `.harness/` are written, reviewed and approved by a human before any
  implementation code exists. Approval is recorded as the git tag `harness-approved`.
- After that tag, the implementing agent must not add, edit, delete or weaken any file under
  `tests/` or `.harness/`. It must not lower thresholds, skip or xfail tests, or bypass a gate.
- Check: `git diff --name-only harness-approved..HEAD -- tests .harness` is empty for every
  implementation or repair commit. A checksum manifest in `.harness/` must match.
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
- If the harness is still red after attempt 2, work stops and a human review is opened. A third
  `repair` commit fails the gate.

### XI. Static Typing (additional)

- All public functions, methods and class attributes in `src/` have type annotations.
- `mypy --strict src` reports zero errors. Ruff `ANN` rules are enabled.

### XII. Hermetic, Fast, Order-Independent Tests (additional)

- Tests do no network I/O, write no files outside `tmp_path`, do not sleep and do not read the
  wall clock.
- The suite passes in its default order and in reverse order (`pytest -p no:randomly` plus
  a reversed-collection hook in `.harness/`), with identical results.
- Full-suite wall time is under 10 seconds on the reference machine. This keeps the tests
  free of real time.

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
- `pip-audit` reports zero known vulnerabilities for the pinned set.

### XVI. Numeric Determinism (additional)

- Token arithmetic gives the same results on every platform. Token counts and clock readings in
  core logic are typed `int` (fixed units) or `Fraction`, never `float`. Check: mypy annotations
  plus an AST scan for `float` in `src/` core modules. The representation is chosen in `plan.md`.
- `Retry-After` is a whole number of seconds ≥ 1, rounded up from the exact wait time. This is
  verified by ACs covering boundary values.

## Quality Gates (Harness)

The harness runs these gates in order, and each must pass for a change to be accepted:

| Gate | Command / check | Pass condition |
|------|-----------------|----------------|
| G1 Protection | diff vs `harness-approved` + checksum manifest | empty diff, checksums match |
| G2 Suppressions | `rg` for suppression comments and disabled rules | zero matches |
| G3 Lint/format | `ruff check .` and `ruff format --check .` | zero findings |
| G4 Security | `bandit -r src` | zero findings |
| G5 Types | `mypy --strict src` | zero errors |
| G6 Clock purity | AST scan for wall-clock and `random` use | zero hits outside clock adapter |
| G7 Size/complexity | AST length script and ruff `C901` | ≤ 40 lines, CC ≤ 10 |
| G8 Traceability | AC ↔ test mapping script | zero orphans either way |
| G9 Tests | `pytest` normal and reverse order | all pass, < 10 s |
| G10 Coverage | `coverage report --fail-under=90` (branch) | ≥ 90 % |
| G11 Secrets | secret scanner over tree and history | zero findings |
| G12 Dependencies | `pip-audit` and justification check against `plan.md` | zero vulns, all justified |
| G13 Repair budget | count of `repair(` commits after `impl-baseline` | ≤ 2 |

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

**Version**: 1.0.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
