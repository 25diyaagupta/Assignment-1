<!--
Sync Impact Report
- Version change: (template) → 1.0.0 (initial ratification)
- Added principles: I–XII (one per project rule 1–12)
- Added sections: Quality Gates (Harness), Development Workflow, Governance, Change Notes
- Removed sections: none
- Templates requiring updates: none (plan/spec/tasks templates read this file at runtime)
- Deferred TODOs: none. Provider SDK choice, threshold value and scoring formula are deferred
  by design to plan.md / spec.md (Principles I and VI), not left as placeholders here.
-->

# Natural-Language Reminder Agent Constitution

Scope: a Python service that takes free text plus a request context (`now`, `timezone`) and
returns one structured JSON decision: `create`, `reschedule`, `snooze`, `clarify` or `refuse`.
A language model is used to interpret the text; an evaluation harness measures the result.

Every principle below is phrased so that a tool, script or `git` query can return pass/fail.
"Harness" means the gate scripts under `.harness/`, run by one command that exits 0 only when
all gates pass. A check marked **(review)** is done by the human reviewer using the checklist in
Governance and is not a harness gate. "Rule n" refers to the project brief item it encodes.

## Core Principles

### I. Python 3.12 and One Thin Model Client (Rule 1)

- The package declares `requires-python = ">=3.12,<3.13"`; the harness runs on CPython 3.12.
- Exactly one module, `src/reminder_agent/model_client.py`, talks to the model. It is the only
  file in `src/` that imports the provider SDK or any HTTP library, and it holds no prompt text,
  parsing or decision logic: it sends a prompt and returns raw text or a typed error.
- Every other module receives the client through a parameter (a `ModelClient` protocol), so
  tests use a fake client and make no network calls.
- Every dependency beyond the standard library (runtime, dev and test) is listed in `plan.md`
  with a one-line justification. Check (review): a dependency with no entry fails review.

### II. Zero Lint and Security Findings, No Suppressions (Rule 2)

- `ruff check` and `ruff format --check` over `src tests .harness` report zero findings. `src/`
  and `.harness/` use the full rule set in `pyproject.toml`; `tests/` may use a smaller rule set
  in `tests/ruff.toml`, with each omitted rule family justified in `plan.md`. Neither file has
  `ignore`, `extend-ignore`, `per-file-ignores` or `exclude` entries.
- `bandit -r src .harness` reports zero findings at every severity and confidence level.
- No `*.py` file has a `noqa`, `nosec`, `type: ignore`, `pragma: no cover` or `fmt: off`
  comment. Check: `rg` for that comment syntax over `*.py` returns no matches.

### III. Unique IDs and Full Traceability (Rule 3)

- Every requirement has an ID `FR-nnn`, every invariant `INV-nnn`, every property `PROP-nnn`
  (three digits), each defined exactly once in `spec.md`.
- Every evaluation case in `evals/dataset.json` has a unique `id` (`EVAL-nnn`) and a non-empty
  `covers` list of those IDs. Every pytest test names the IDs it covers in a
  `@pytest.mark.covers(...)` marker.
- Check (harness, G8): zero cases with an empty `covers`, zero references to IDs not defined in
  `spec.md`, and every `FR`/`INV`/`PROP` ID cited by at least one evaluation case or test.

### IV. Injected Time and Timezone (Rule 4)

- Every request carries `now` (ISO 8601 with UTC offset) and `timezone` (IANA name). All
  relative expressions ("tomorrow", "in 2 hours", "next Monday") resolve against these values.
- Code never reads the wall clock. Check (harness, G7): `rg` over `src/` and `prompts/` for
  `datetime.now`, `datetime.today`, `datetime.utcnow`, `date.today`, `time.time`,
  `time.monotonic`, `time.localtime` and `time.gmtime` returns no matches.
- The model client's timeout uses a configured duration, not a clock read by agent logic.

### V. Fixed Output Schema (Rule 5)

- The output schema (field names, types, required/optional, and the `decision` enumeration
  `create | reschedule | snooze | clarify | refuse`) is defined in `spec.md` and mirrored as
  a JSON Schema file at `.harness/output.schema.json`.
- The schema is independent of prompt or model wording: a change to `prompts/` or to the model
  never changes field names, types or enumerations. Model output is parsed and validated against
  the schema in code; text that does not validate is never returned to the caller as-is.
- The schema changes only through a spec amendment (Governance) and a new `baseline` tag.

### VI. Evaluation Contract Declared Up Front, Never Lowered (Rule 6)

- `spec.md` declares the scoring method (what counts as a pass per layer, how cases combine
  into a score, how service errors are treated per Principle X) and the numeric pass threshold
  before the `baseline` tag. The harness reads the same values from `.harness/eval_config.json`.
- After declaration the threshold is never lowered and the scoring method never relaxed.
  Check (harness, G1): `.harness/` is unchanged since `baseline`. Check (review): `git log -p`
  on `spec.md` shows no decrease of the threshold line.

### VII. Three-Layer Evaluation Pipeline (Rule 7)

- One command runs all three layers on every case, in order:
  - **L1 Structure**: output parses as JSON and validates against the output schema.
  - **L2 Invariants and properties**: deterministic code checks for each `INV`/`PROP`, for
    example "a `create` due time is after `now`", "`refuse` and `clarify` carry no due time",
    "`clarify` carries a non-empty question", "the due time is expressed in the request
    timezone".
  - **L3 Semantic quality**: decision and key fields compared with the case's expected values.
- A case passes only if L1, L2 and L3 all pass. A case failing L1 is not scored by L2 or L3.
- An LLM judge, if used, runs only inside L3 and never replaces or overrides L1 or L2.

### VIII. Protected Dataset, Harness and Tests (Rule 8)

- `evals/dataset.json`, `.harness/` and `tests/` are written and approved by a human before
  any implementation code exists. Approval is the git tag `baseline`.
- After `baseline`, implementation and repair commits change only `src/` and `prompts/`.
  Check (harness, G1): `git diff --name-only baseline..HEAD -- evals/dataset.json .harness tests`
  is empty, and every repair commit touches no path outside `src/` and `prompts/`.
- A change to protected files needs a human-approved spec amendment and a new tag
  `baseline-vN`.

### IX. No Secrets in the Repository (Rule 9)

- The API key lives only in `.env`, which is listed in `.gitignore` and never committed.
  A committed `.env.example` holds variable names with empty values.
- Check (harness, G6): `git ls-files .env` is empty, and `detect-secrets scan` over `src`,
  `prompts`, `tests`, `.harness`, `evals` and the root config files reports zero findings with
  at least one file scanned. (`.specify/` is out of scope: its manifest hashes are not secrets.)
- Harness reports and logs never contain the key or request headers.

### X. Service Errors Recorded Apart From Wrong Answers (Rule 10)

- The model client maps timeout, rate-limit and unavailable conditions to typed errors
  (`ModelTimeout`, `ModelRateLimited`, `ModelUnavailable`).
- The harness records each case outcome as exactly one of `pass`, `fail` (wrong answer at L1,
  L2 or L3) or `error` (service error), and reports the three counts separately. An `error` is
  never counted as `fail`, and a `fail` is never relabelled as `error`.
- How `error` cases enter the score is fixed in the scoring method (Principle VI).

### XI. First Generation Preserved, Bounded Repair (Rule 11)

- The first generated implementation, and its first harness report, are committed unchanged
  and tagged `gen-1` before any repair.
- Each repair cycle allows at most 2 attempts, each a separate commit whose message starts
  `repair(1/2):` or `repair(2/2):`. If the harness is still red after attempt 2, work stops
  and a human review is opened before any further change.
  Check (review): a third `repair` commit in one cycle fails review.

### XII. Synthetic Evaluation Inputs (Rule 12)

- Every input in `evals/dataset.json` is invented for this project. No text comes from real
  messages, calendars or people, and the dataset declares `"synthetic": true`.
- Check (harness, G8): no input contains an e-mail address, phone number or URL pattern.
  Check (review): names and places are clearly fictional.

## Quality Gates (Harness)

The harness runs these gates in order; each must pass for a change to be accepted:

| Gate | Command / check | Pass condition |
|------|-----------------|----------------|
| G1 Integrity | `git diff --name-only baseline..HEAD -- evals/dataset.json .harness tests` | empty diff |
| G2 Suppressions | `rg` for suppression comment syntax in `*.py` | zero matches |
| G3 Lint/format | `ruff check` and `ruff format --check` over `src tests .harness` | zero findings |
| G4 Security | `bandit -r src .harness` | zero findings |
| G5 Unit tests | `pytest` with the fake model client, network disabled | all pass |
| G6 Secrets | `.env` untracked; `detect-secrets scan` over the scoped paths | zero findings |
| G7 Clock | `rg` for wall-clock calls over `src/` and `prompts/` | zero matches |
| G8 Dataset | ID traceability (III) and synthetic-input scan (XII) | zero violations |
| G9 Evaluation | L1 → L2 → L3 over `evals/dataset.json` with the real model client | score ≥ declared threshold; `pass`/`fail`/`error` counts reported |

G1–G8 make no model calls. G9 is the only gate that uses the network and the key.

## Development Workflow

1. `/speckit-specify` then `/speckit-clarify`: `spec.md` with `FR`/`INV`/`PROP` IDs, the output
   schema, the scoring method and the threshold.
2. `/speckit-plan`: `plan.md` with dependencies and justifications, the `ModelClient` protocol,
   error mapping and the module map. Runs the Constitution Check.
3. `/speckit-tasks`. Write `evals/dataset.json`, `.harness/` and `tests/`; tests fail (red).
   A human approves; tag `baseline`.
4. `/speckit-implement`. Commit the first output and its harness report unchanged; tag `gen-1`.
5. Run the harness. If red, at most 2 `repair(n/2)` commits touching only `src/` and
   `prompts/`. If still red, human review.

## Governance

- This constitution overrides every other practice in the project. `/speckit-plan` and
  `/speckit-analyze` check plans and tasks against it; any violation is CRITICAL.
- Amendments are made only through `/speckit-constitution`, with a dated change note and a
  semantic version bump: MAJOR when a principle is removed or redefined, MINOR when one is added
  or materially expanded, PATCH for wording only.
- No implementing agent may amend this constitution, the threshold or the scoring method.
  Amendments need human approval.
- Every review confirms all harness gates are green and works through these **(review)**
  checks: every dependency justified (I); threshold never lowered in `spec.md` history (VI);
  at most 2 `repair` commits per cycle and `gen-1` untouched (XI); dataset names and places
  fictional (XII).

## Change Notes

- **2026-11-22** (Deepanshi Bansal, with Claude), template → v1.0.0: initial ratification.
  Principles I–XII encode project rules 1–12. Lessons carried over from Part-1A: the smaller
  documented ruff rule set for `tests/` (II) and the project-scoped secret scan (IX) are in
  place from the start.

**Version**: 1.0.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
