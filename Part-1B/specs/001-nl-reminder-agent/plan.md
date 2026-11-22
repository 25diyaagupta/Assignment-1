# Implementation Plan: Natural-Language Reminder Agent

**Branch**: `001-nl-reminder-agent` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-nl-reminder-agent/spec.md`

## Summary

A Python 3.12 library (with a thin CLI) that turns free text plus an injected `now` and IANA
timezone into one seven-key JSON decision. Google Gemini, called over its REST API from a single
module using the standard library's `http.client`, interprets the language. Everything else is
deterministic code: request validation, a calendar context built from the injected `now`, parsing
of the model's reply, **all date arithmetic** (the model returns a local wall time or a duration,
code attaches the offset, checks daylight-saving gaps and "not before now"), output validation and
a leak guard. An evaluation harness under `.harness/` runs every dataset case three times through
L1 structure, L2 invariants/properties and L3 scoring, and applies the threshold declared in the
spec. Runtime dependencies: none beyond the standard library.

## Technical Context

**Language/Version**: Python 3.12 (`requires-python = ">=3.12,<3.13"`; local interpreter
`python3.12`, environment managed with `uv`)

**Primary Dependencies**: runtime — standard library only (`http.client`, `ssl`, `json`,
`zoneinfo`, `dataclasses`). Dev/test — see §Dependencies.

**Storage**: none. Inputs/outputs are JSON; the dataset is a versioned JSON file; harness reports
are written to `reports/`.

**Testing**: pytest with a `FakeModelClient`; network disabled in `tests/conftest.py`; coverage
≥ 90% branch on `src/`.

**Target Platform**: Linux with CPython 3.12 and the system IANA timezone database; harness gate
runner is bash.

**Project Type**: single library + CLI (`python -m reminder_agent`).

**Performance Goals**: none declared in the spec (low impact, see clarify coverage). Practical
bound: one model call per request; harness paces calls to stay within the Gemini free-tier
request rate.

**Constraints**: no wall-clock reads in `src/`/`prompts/` (G7); zero ruff/bandit findings with no
suppressions (G2–G4); the key only in `.env` (G6); exactly one module talks to the network.

**Scale/Scope**: 30 evaluation cases × 3 repetitions = 90 model calls per G9 run.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design (below).*

| # | Principle | How this plan complies | Status |
|---|---|---|---|
| I | Python 3.12, one thin client | `src/reminder_agent/model_client.py` is the only file importing `http.client`/`ssl`; it holds no prompt text, parsing or decision logic. Others receive a `ModelClient` protocol (defined in `ports.py`, which imports nothing from the network). Every dependency is justified in §Dependencies. | PASS |
| II | Zero lint/security, no suppressions | Full ruff rule set (Part-1A set) for `src/` and `.harness/`; smaller set in `tests/ruff.toml` justified below. `http.client.HTTPSConnection` is used instead of `urllib.request.urlopen`, which ruff S310 / bandit B310 flag and could only be silenced by a forbidden suppression. Harness Python makes no `subprocess` calls (B404/B603/S603 would fire); process calls live in `gates.sh`. | PASS |
| III | IDs and traceability | Tests use `@pytest.mark.covers("FR-…", …)` (registered with `--strict-markers`); dataset cases carry `id` and `covers`; G8 checks both against IDs parsed from `spec.md`. | PASS |
| IV | Injected time | `Request.now`/`Request.timezone` are the only time sources; calendar context, durations and DST handling are computed from them with `zoneinfo`. HTTP timeout is a configured number of seconds passed to `HTTPSConnection(timeout=…)`. G7 greps `src/` and `prompts/`. | PASS |
| V | Fixed output schema | Spec Output Schema mirrored at `.harness/output.schema.json` (draft in `contracts/output.schema.json`). Agent validates its own output in code (`output.py`) before returning; invalid model text raises `InvalidModelOutput`, never passed through. | PASS |
| VI | Evaluation contract up front | Weights, threshold, repetitions, guardrail bar and error cap copied from the spec into `.harness/eval_config.json` before the tag. | PASS |
| VII | Three-layer pipeline | `.harness/evaluate.py`: L1 (`jsonschema`), L2 (INV-005..007, PROP-001..006), L3 (weighted score). L1 failure skips L2/L3. No LLM judge. | PASS |
| VIII | Protected dataset/harness/tests | `evals/dataset.json`, `.harness/`, `tests/` written and approved first; tag `baseline-1b-before-implement`; G1 diff check. | PASS |
| IX | No secrets | `GEMINI_API_KEY` only in `.env` (already git-ignored); `.env.example` committed with empty values; key sent only in the `x-goog-api-key` header, never in the URL; reports never include headers. G6 runs `detect-secrets` on the scoped paths. | PASS |
| X | Service errors apart | Client maps transport/HTTP failures to `ModelTimeout`, `ModelRateLimited`, `ModelUnavailable`; harness labels those repetitions `error`. Auth/config failures raise `ModelConfigError`, which aborts the run (not 90 `error`s). | PASS |
| XI | First generation preserved | Workflow steps 4–5 unchanged; repair commits `repair(1/2)`/`repair(2/2)` touch `src/` and `prompts/` only. | PASS |
| XII | Synthetic inputs | Dataset declares `"synthetic": true`; G8 scans inputs for e-mail, phone and URL patterns. | PASS |

No violations; Complexity Tracking is empty.

## Architecture

```text
Request(text, now, timezone)
  │  request.py ─ validate (FR-003) ── InvalidRequest (no model call)
  ▼
calendar_facts.py ─ facts from now/tz: local date, weekday, next 14 dates with weekday names, offset
  ▼
prompt.py ─ system text from prompts/system.md + user message (text, now, tz, calendar facts)
  ▼
ModelClient.generate(system, user, response_schema) ── typed service errors
  ▼
interpretation.py ─ parse model JSON into Interpretation (decision, task, due_local,
  │                  relative_minutes, reminder_ref, snooze_minutes, question, refusal_reason)
  │                  invalid → InvalidModelOutput
  ▼
resolve.py ─ due = now + relative_minutes, or due_local attached to tz via zoneinfo;
  │          non-existent/ambiguous DST wall time → clarify; due < now → clarify (INV-006)
  ▼
guard.py ─ output contains prompt run ≥ 40 chars / canary / secret → refuse prompt_extraction
  ▼
output.py ─ build DecisionOutput, enforce per-decision null rules (INV-003/004), to_json
```

Key design choice (research R3): the model never does date arithmetic. It identifies *what*
time was meant (a local wall time or a duration in minutes) and code computes the instant and
offset. This targets the 0.3-weight exact-due component and PROP-002/INV-007, which language
models get wrong most often (DST, month/year rollover).

## Project Structure

### Documentation (this feature)

```text
specs/001-nl-reminder-agent/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── agent-api.md         # handle_request + CLI contract
│   ├── model-client.md      # ModelClient protocol, Gemini REST mapping, error mapping
│   ├── output.schema.json   # draft of .harness/output.schema.json
│   └── dataset-format.md    # evals/dataset.json and eval_config.json format
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/reminder_agent/
├── __init__.py          # exports handle_request, Request, DecisionOutput, errors
├── __main__.py          # CLI: JSON request on stdin → decision JSON on stdout
├── ports.py             # ModelClient Protocol (no network imports)
├── errors.py            # ModelTimeout, ModelRateLimited, ModelUnavailable, ModelConfigError,
│                        # InvalidRequest, InvalidModelOutput
├── model_client.py      # GeminiClient — the ONLY network module (http.client + ssl)
├── request.py           # Request dataclass + validation (FR-001, FR-003)
├── calendar_facts.py    # calendar facts derived from injected now/tz (FR-006)
├── prompt.py            # loads prompts/system.md, builds user message and response schema
├── interpretation.py    # parse/validate model JSON → Interpretation
├── resolve.py           # due resolution, DST, not-before-now (FR-006, FR-008, INV-005..007)
├── guard.py             # leak guard (PROP-004)
├── output.py            # DecisionOutput, per-decision rules, JSON serialisation (FR-002, INV-*)
└── agent.py             # handle_request(request, client) orchestration

prompts/
└── system.md            # system instructions incl. canary marker (changeable in repair)

tests/                   # PROTECTED after baseline-1b-before-implement
├── conftest.py          # FakeModelClient, network block, fixtures
├── ruff.toml
├── test_us1_create.py
├── test_us2_clarify.py
├── test_us3_reschedule_snooze.py
├── test_us4_guardrails.py
├── test_us5_scoring.py  # harness scoring/threshold with scripted outputs (FR-019..024)
├── test_request_validation.py  # FR-003
├── test_model_client.py        # HTTP/error mapping against a local stub connection
└── test_dataset.py             # FR-025/026 dataset shape and coverage

evals/
└── dataset.json         # PROTECTED; 30 synthetic cases, "synthetic": true

.harness/                # PROTECTED
├── gates.sh             # G1–G9 in order, exit 0 only if all pass; --offline runs G1–G8
├── evaluate.py          # G9: L1 → L2 → L3, 3 repetitions, writes reports/
├── scoring.py           # pure scoring + threshold functions (imported by evaluate.py, tests)
├── check_dataset.py     # G8: traceability + synthetic-input scan
├── output.schema.json
└── eval_config.json

reports/                 # harness run reports (JSON + Markdown); gen-1 report committed
pyproject.toml  requirements-dev.txt  .env.example  CLAUDE.md
```

**Structure Decision**: single project, `src/` layout as in Part-1A. Prompt text lives in
`prompts/` so repairs can change wording without touching code logic, as Principles VIII/XI
expect.

## Dependencies

| Package (pinned in `requirements-dev.txt`) | Scope | Justification |
|---|---|---|
| *(none)* | runtime | `http.client`+`ssl` cover one JSON POST; `zoneinfo` covers DST; a hand-written validator in `output.py` covers the seven-key schema. A Gemini SDK would add a large transitive tree for one endpoint. |
| `pytest==9.2.0` | test | Test runner; `covers` markers (III); same version as Part-1A. |
| `coverage==7.17.4` | test | Branch coverage ≥ 90% on `src/`. |
| `ruff==0.17.6` | dev | Gates G2/G3 (lint + format). |
| `bandit==1.9.4` | dev | Gate G4. |
| `detect-secrets==1.5.0` | dev | Gate G6. |
| `jsonschema==4.25.1` | dev (harness) | L1 validates against `.harness/output.schema.json` with an implementation independent of the agent's own validator, so the harness does not grade the agent with the agent's code. |
| System: `bash`, `git`, `rg` | harness | `gates.sh`, G1 diff, G2/G7 searches. Taken from the OS, not pinned. |

Rejected: `google-genai` SDK (unneeded weight; would need a runtime dependency and a second
module talking to the network indirectly), `requests`/`httpx` (stdlib suffices), `python-dotenv`
(`gates.sh` loads `.env` with `set -a; . ./.env`), `pytest-socket` (a five-line socket block in
`conftest.py` does the same), `tzdata` (Linux system database is the target).

## Ruff Rule Sets

- `src/`, `.harness/`: `E F W I B C90 D ANN S UP SIM PL`, mccabe ≤ 10, Google docstrings
  (identical to Part-1A).
- `tests/` (`tests/ruff.toml`): `E F W I B C90 UP SIM`. Omitted: `S` (S101 forbids `assert`, which
  pytest needs), `PL` (PLR2004 magic values are the expected literals of a test), `D` and `ANN`
  (test names and fixtures document themselves; requiring docstrings/annotations adds noise).

## Harness Gates (implements constitution table)

| Gate | Implementation |
|---|---|
| G1 | `git diff --name-only baseline-1b-before-implement..HEAD -- evals/dataset.json .harness tests` empty; passes with a warning before the tag exists. |
| G2 | `rg -n '#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no cover|fmt:\s*off)' -g '*.py'` → no matches. |
| G3 | `ruff check src tests .harness` and `ruff format --check src tests .harness`. |
| G4 | `bandit -r src .harness` with default settings (reports every severity and confidence); zero findings. |
| G5 | `coverage run -m pytest` then `coverage report` (fail_under 90). |
| G6 | `git ls-files .env` empty; `detect-secrets scan` over `src prompts tests .harness evals pyproject.toml requirements-dev.txt .gitignore .env.example`, zero results and ≥ 1 file scanned. |
| G7 | `rg` for the eight wall-clock calls over `src/` and `prompts/` → no matches. |
| G8 | `python .harness/check_dataset.py`. |
| G9 | `python .harness/evaluate.py` with the real `GeminiClient`; exit 0 only if the threshold holds. |

## Post-Design Constitution Re-check

Re-checked after writing research.md, data-model.md and contracts/: the design adds no network
module besides `model_client.py`, no wall-clock call (pacing between harness calls uses
`time.sleep` inside `.harness/evaluate.py`, outside G7's scope and not a clock read), no runtime
dependency, and the schema in `contracts/output.schema.json` matches the spec table. All twelve
principles remain PASS.

## Complexity Tracking

No violations to justify.
