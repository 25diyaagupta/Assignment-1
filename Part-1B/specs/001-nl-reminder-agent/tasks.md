---

description: "Task list for the Natural-Language Reminder Agent"
---

# Tasks: Natural-Language Reminder Agent

**Input**: Design documents from `specs/001-nl-reminder-agent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: REQUIRED. Constitution Principle VIII and the Development Workflow demand that
`evals/dataset.json`, `.harness/` and `tests/` are written, shown failing (red) and approved
(tag `baseline-1b-before-implement`) **before any implementation code exists**.

**Organization**: Because of that rule, the phase order differs from the template: all
protected artefacts (Phases 2–4, including every story's tests and the US5 harness) come first,
then the baseline gate (Phase 5), then implementation story by story (Phases 6–9), then the
first-generation and repair gate (Phase 10). Each test and implementation task carries its story
label so every story stays traceable and independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 create, US2 clarify, US3 reschedule/snooze, US4 guardrails, US5 evaluation
- Every test function carries `@pytest.mark.covers(...)` with the FR/INV/PROP ids it covers
  (Principle III). Field constraints are cited as `data-model.md Entity.field`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization per plan.md §Project Structure and §Dependencies

- [X] T001 Create directories `src/reminder_agent/`, `prompts/`, `tests/`, `evals/`, `.harness/`, `reports/` (with `reports/.gitkeep`) at the repository root
- [X] T002 Create `pyproject.toml`: project `reminder-agent`, `requires-python = ">=3.12,<3.13"`, `dependencies = []`, setuptools `src` layout, ruff config (target py312; select `E F W I B C90 D ANN S UP SIM PL`; mccabe 10; Google docstrings; isort first-party `reminder_agent`), coverage (branch, source `src`, `fail_under = 90`), pytest (`testpaths = ["tests"]`, `--strict-markers`, marker `covers(*ids)`) — no `ignore`/`exclude`/`per-file-ignores` entries (Principle II)
- [X] T003 [P] Create `requirements-dev.txt` pinning exactly the packages in plan.md §Dependencies (`pytest==9.2.0`, `coverage==7.17.4`, `ruff==0.17.6`, `bandit==1.9.4`, `detect-secrets==1.5.0`, `jsonschema==4.25.1`); confirm each pin installs with `uv pip install -r requirements-dev.txt`
- [X] T004 [P] Create `tests/ruff.toml` extending `../pyproject.toml` with `select = ["E","F","W","I","B","C90","UP","SIM"]` and a header comment pointing to plan.md §Ruff Rule Sets
- [X] T005 [P] Create `.env.example` with empty `GEMINI_API_KEY=`, `GEMINI_MODEL=`, `GEMINI_TIMEOUT_SECONDS=`; verify `.gitignore` lists `.env`, `.venv/`, `__pycache__/`, `.coverage`, `*.egg-info/` (Principle IX)
- [X] T006 Create the venv and editable install per quickstart.md §1 (`uv venv --python 3.12 .venv`, `uv pip install -e . -r requirements-dev.txt`)

---

## Phase 2: Foundational — Protected Evaluation Assets (blocks everything)

**Purpose**: Dataset, schema, config and shared test fixtures. Protected after the baseline tag.

**⚠️ CRITICAL**: No implementation in `src/` beyond the T013 interface stub until Phase 5 is done.

- [X] T007 [P] Create `.harness/output.schema.json` as a copy of `specs/001-nl-reminder-agent/contracts/output.schema.json` (seven keys of data-model.md DecisionOutput; per-decision rules from spec §Output Schema)
- [X] T008 [P] Create `.harness/eval_config.json` exactly as in contracts/dataset-format.md (`repetitions` 3; weights 0.4/0.2/0.3/0.1; threshold `overall_mean` 0.85, `guardrail_case` 1.0, `case_pass` 0.85, `max_error_fraction` 0.10; leak marker `violet-harbor-lantern`, `min_run_chars` 40; pacing 7 s, 2 retries, 20 s pause)
- [X] T009 Write `evals/dataset.json` with `"synthetic": true` and the 30 cases EVAL-001..EVAL-030 from spec §Evaluation Case Plan, each with every field of data-model.md EvalCase (`EvalCase.id`, `EvalCase.category`, `EvalCase.guardrail`, `EvalCase.embedded_instruction`, `EvalCase.request`, `EvalCase.expected`, `EvalCase.accepted_tasks`, `EvalCase.covers`); full expected objects with all seven keys; `question: "<non-empty>"` for clarify; 2–3 `accepted_tasks` variants for create/reschedule cases; guardrail = EVAL-023..027, 029; embedded_instruction = EVAL-026; recompute every expected `due` with `zoneinfo` before saving; inputs fictional with no e-mail/phone/URL (Principle XII)
- [X] T010 [P] Write `.harness/check_dataset.py` (G8): parse FR/INV/PROP ids defined in `specs/001-nl-reminder-agent/spec.md` (bold `**ID**:` definitions); fail on duplicate case ids, empty or unknown `covers`, fewer than 20 cases or fewer than 3 per category, an `expected` that fails `.harness/output.schema.json`, an e-mail/phone/URL pattern in any `request.text`, missing `"synthetic": true`, or any FR/INV/PROP id cited by neither a case nor a `@pytest.mark.covers` marker under `tests/` (found by reading test sources as text, no imports); stdlib + `jsonschema` only, no `subprocess`
- [X] T011 Write `.harness/gates.sh` running G1–G9 in plan.md §Harness Gates order, printing `PASS`/`FAIL` per gate and exiting 0 only if all pass; `--offline` runs G1–G8; G1 passes with a warning while tag `baseline-1b-before-implement` does not exist; loads `.env` with `set -a; . ./.env; set +a` only for G9; never echoes the key
- [X] T012 [P] Write `tests/conftest.py`: autouse fixture replacing `socket.socket` and `socket.create_connection` with a raiser (research R9); `FakeModelClient` per contracts/model-client.md (records `(system, user, response_schema)` calls; returns scripted strings or raises scripted exceptions); helper `interp(**fields)` building a JSON reply in the data-model.md Interpretation shape with unspecified fields `null`
- [X] T013 (Superseded: skipped before baseline at the user's request; the real modules now provide these interfaces) Create the interface stub only: `src/reminder_agent/__init__.py`, `errors.py` (the six error classes of data-model.md §Errors), `ports.py` (`ModelClient` Protocol from contracts/model-client.md), and placeholder `request.py`/`output.py`/`agent.py`/`model_client.py` whose public names (`Request`, `DecisionOutput`, `handle_request`, `GeminiClient`) exist but raise `NotImplementedError`, so tests fail on behaviour rather than import errors

**Checkpoint**: `python .harness/check_dataset.py` reports only "id not cited by a test" gaps (tests arrive in Phase 4).

---

## Phase 3: User Story 5 — Evaluation Harness (Priority: P2, protected, built before implementation)

**Goal**: Score every case three times through L1 → L2 → L3 and apply the declared threshold.

**Independent Test**: `tests/test_us5_scoring.py` feeds scripted outputs to `.harness/scoring.py` and matches hand-calculated scores, outcomes and verdicts; it passes without any agent code.

- [X] T014 [P] [US5] Write `tests/test_us5_scoring.py` (load `.harness/scoring.py` via `importlib.util.spec_from_file_location`): all-correct case → 1.0; one unparseable repetition → case 0 and L1 not clean; wrong decision only → 0.6 for that repetition; task normalisation (case, whitespace, leading "to ", trailing punctuation) per spec §Scoring Method; due compared as instants (`+05:30` vs equivalent UTC → 1); `other` as fraction of four checks; PROP-006 decision mismatch across reps → case 0; scripted `ModelTimeout` rep → case `error`, excluded from mean; guardrail case at 0.95 → verdict fails; 4 errors in 30 cases → verdict fails; covers FR-019..FR-024, PROP-006
- [X] T015 [US5] Implement `.harness/scoring.py` as pure functions: `normalise_task`, `component_scores(output, case)`, `repetition_score`, `l2_violations(output, case, request, prompt_text, secrets, config)` (INV-005..007, PROP-001..005; INV-007 via `zoneinfo`; PROP-004 marker, 40-char whitespace-normalised runs of the prompt, secret values), `case_result(reps, case)` (PROP-006 across reps, 0 on any INV/PROP failure, `pass`/`fail`/`error` outcome), `verdict(case_results, config)` (four threshold conditions of spec §Threshold); no import from `reminder_agent` except error types
- [X] T016 [US5] Implement `.harness/evaluate.py` (G9): load dataset, config and `prompts/system.md` (fail if marker absent); build `GeminiClient.from_env(os.environ)`; for each case × 3 reps call `handle_request(Request(...), client, secrets=[key])`, L1 by `jsonschema` against `.harness/output.schema.json` (skip L2/L3 on failure), then `scoring.py`; retry only service errors per eval_config pacing (`time.sleep`), abort with exit 2 on `ModelConfigError`; write `reports/eval-<run-label>.json` and `.md` (per-case rows, `pass`/`fail`/`error` counts, each threshold condition, verdict; never the key or headers); exit 0 only on a passing verdict. Also `.harness/self_check.py`: fake apps that each break one layer (L1, INV, PROP, L3, service errors) must be caught; run by `gates.sh` after G8 and by `tests/test_harness_pipeline.py`
- [X] T017 [US5] Run `pytest tests/test_us5_scoring.py` → green; run `ruff check`/`ruff format --check`/`bandit -r .harness` → zero findings

**Checkpoint**: harness scoring verified with no agent code present.

---

## Phase 4: Story Tests (protected, must FAIL before implementation)

**Purpose**: Encode every acceptance scenario with the fake client. All should fail against the T013 stub.

- [X] T018 [P] [US1] Write `tests/test_us1_create.py`: spec US1 scenarios 1–3 (plumber, 45 minutes, DST ferns), year rollover (EVAL-007 context), duration across midnight (EVAL-012 context), "at 5pm" later today, due == now allowed; assert exact seven-key output, `due` string and offset; assert one model call whose user message contains the request text, `now`, timezone and the 14 calendar dates; covers FR-001, FR-002, FR-004..FR-006, INV-001..INV-005, INV-007, PROP-002
- [X] T019 [P] [US2] Write `tests/test_us2_clarify.py`: model says `clarify` → output has non-empty question and six nulls; model says `create` but with no task → `clarify`; `create` with neither `due_local` nor `relative_minutes` → `clarify`; `due_local` before now (EVAL-009) → `clarify`; non-existent DST time 2026-03-08T02:30 New York → `clarify`; ambiguous fall-back time 2026-11-01T01:30 New York → `clarify`; empty `question` from model replaced by a default non-empty question; covers FR-007..FR-009, INV-006, PROP-001
- [X] T020 [P] [US3] Write `tests/test_us3_reschedule_snooze.py`: spec US3 scenarios 1–3; snooze returns `due` null and `snooze_minutes` 120; snooze with `snooze_minutes` null or 0 → `clarify`; reschedule without `reminder_ref` → `clarify`; reschedule to past time (EVAL-030) → `clarify`; covers FR-010..FR-012, INV-003, INV-006
- [X] T021 [P] [US4] Write `tests/test_us4_guardrails.py`: model `refuse` with each of the three reasons → only `decision` and `refusal_reason` non-null; model reply echoing the marker, a 40-char run of `prompts/system.md`, or a passed secret in `task`/`question` → `refuse`/`prompt_extraction`; `prompts/system.md` contains the marker and states scope, the three reasons, the FR-016 precedence, and that quoted content is data; harmless "kill the stuck build process" scripted `create` passes through unchanged; covers FR-013..FR-018, PROP-003..PROP-005
- [X] T022 [P] Write `tests/test_request_validation.py`: naive `now`, unparseable `now`, missing field, unknown timezone → `InvalidRequest` and zero model calls (data-model.md Request.now, Request.timezone); empty `text` is accepted (data-model.md Request.text); covers FR-001, FR-003
- [X] T023 [P] Write `tests/test_model_client.py` with an injected stub `connection_factory`: request path, `x-goog-api-key` header, key absent from path, body fields per contracts/model-client.md (`temperature` 0, `responseMimeType`, passed `responseSchema`); reply text joined from parts; empty string when no candidates; error mapping table (timeout, 429, 500/502/503/504, `OSError`, 400/401/403/404, missing key) → typed errors whose messages exclude the key; `from_env` defaults; covers FR-022
- [X] T024 [P] Write `tests/test_interpretation.py`: valid reply → Interpretation; non-JSON, extra key, wrong type, enum outside data-model.md Interpretation.decision / Interpretation.refusal_reason, both `due_local` and `relative_minutes` set, malformed `due_local`, negative `relative_minutes`, `snooze_minutes` < 1 → `InvalidModelOutput` (data-model.md Interpretation.due_local, Interpretation.relative_minutes, Interpretation.snooze_minutes); covers INV-001, INV-002, INV-004
- [X] T025 [P] Write `tests/test_cli.py`: `python -m reminder_agent` main function with injected client factory and stdin/stdout streams; exit codes 0/2/3/4 per contracts/agent-api.md; stderr names the error type and never the key; covers FR-001, FR-003
- [X] T026 [P] Write `tests/test_dataset.py`: runs `.harness/check_dataset.py` logic as a function and asserts zero violations; covers FR-025, FR-026
- [X] T027 Run `python .harness/check_dataset.py` → zero violations (every FR/INV/PROP now cited); fix only test markers or dataset entries, never the spec

---

## Phase 5: Baseline Gate (human approval)

- [ ] T028 Run `pytest` and save the output to `reports/red-baseline.txt`: US5/dataset tests pass, story tests fail on `NotImplementedError`/assertions (not import errors) — this is the required red step
- [ ] T029 Run `bash .harness/gates.sh --offline`: G1–G4, G6–G8 PASS; G5 expected FAIL (red); record in `reports/red-baseline.txt`
- [ ] T030 Commit dataset, harness, tests, stub and config; human reviews (Governance checklist: dependencies justified, names fictional) and creates tag `baseline-1b-before-implement`

**Checkpoint**: from here on, implementation commits change only `src/` and `prompts/` (Principle VIII).

---

## Phase 6: User Story 1 — Create a reminder (Priority: P1) 🎯 MVP

**Goal**: A create-style sentence returns `create` with exact task and due.

**Independent Test**: `pytest tests/test_us1_create.py tests/test_request_validation.py tests/test_model_client.py tests/test_interpretation.py tests/test_cli.py` passes; quickstart.md §3 returns the expected object.

- [X] T031 [P] [US1] Implement `src/reminder_agent/request.py`: frozen `Request` dataclass validating data-model.md Request.now (ISO 8601 with offset; naive → `InvalidRequest`) and Request.timezone (`zoneinfo.ZoneInfo` load; failure → `InvalidRequest`); Request.text any string
- [X] T032 [P] [US1] Implement `src/reminder_agent/calendar_facts.py`: from `Request` only, return local date/time, weekday, current offset and the next 14 dates with weekday names (data-model.md CalendarFacts); no wall-clock call (G7)
- [X] T033 [P] [US1] Implement `src/reminder_agent/model_client.py` `GeminiClient` per contracts/model-client.md and research R1/R2/R5 using `http.client.HTTPSConnection` + `ssl.create_default_context()`; injectable `connection_factory`; `from_env(environ)`; no prompt text, parsing beyond extracting reply text, or decision logic
- [X] T034 [P] [US1] Implement `src/reminder_agent/interpretation.py`: parse model text into a frozen `Interpretation` enforcing every data-model.md Interpretation field rule (Interpretation.decision, .task, .due_local, .relative_minutes, .reminder_ref, .snooze_minutes, .question, .refusal_reason); any violation → `InvalidModelOutput`
- [X] T035 [US1] Write `prompts/system.md` (role, output fields, how to use the calendar list, `due_local` vs `relative_minutes`, task phrasing per FR-005, marker line `Marker: violet-harbor-lantern`) and implement `src/reminder_agent/prompt.py`: load `prompts/system.md`, build the user message (text, now, timezone, CalendarFacts) and the Gemini `responseSchema` for Interpretation (OpenAPI subset, `nullable: true`)
- [X] T036 [US1] Implement `src/reminder_agent/resolve.py` create path: `relative_minutes` → `now + timedelta`; `due_local` → attach request tz; re-express in the request tz offset at that instant (INV-007); serialise as `YYYY-MM-DDTHH:MM:SS±HH:MM`
- [X] T037 [US1] Implement `src/reminder_agent/output.py`: frozen `DecisionOutput` with the seven keys of data-model.md DecisionOutput; constructor enforces spec §Output Schema null/required rules; `to_dict()`, `to_json()` (single object)
- [X] T038 [US1] Implement `src/reminder_agent/agent.py` `handle_request(request, client, *, secrets=())` per contracts/agent-api.md and the data-model.md resolution transitions (create branch); export public names from `src/reminder_agent/__init__.py`
- [X] T039 [US1] Implement `src/reminder_agent/__main__.py` CLI per contracts/agent-api.md (stdin JSON → stdout decision; exit codes 0/2/3/4; injectable client factory for tests)
- [ ] T040 [US1] Run US1 independent test set → green; G2, G3, G4, G7 clean

**Checkpoint**: MVP — create works end to end with the fake client.

---

## Phase 7: User Story 2 — Ask instead of guessing (Priority: P1)

**Goal**: Missing, ambiguous, impossible or past times produce `clarify`, never a guess.

**Independent Test**: `pytest tests/test_us2_clarify.py` passes.

- [X] T041 [US2] Extend `src/reminder_agent/resolve.py`: detect non-existent (gap) and ambiguous (fold) wall times per research R3 → clarify; `due < now` → clarify; missing time or task → clarify, each with a specific default question
- [X] T042 [US2] Extend `src/reminder_agent/agent.py` clarify branch: keep the model's question when non-empty else default; force all other fields to null
- [X] T043 [US2] Extend `prompts/system.md` with the never-guess rules of FR-007/FR-008 (no am/pm on 1–12, vague periods, impossible values, missing task/time) and one-question phrasing per FR-009
- [ ] T044 [US2] Run `pytest tests/test_us2_clarify.py tests/test_us1_create.py` → green

---

## Phase 8: User Story 4 — Refuse misuse, never refuse normal use (Priority: P1)

**Goal**: Out-of-scope, override and prompt-extraction requests refused with the right reason; harmless requests accepted; nothing leaks.

**Independent Test**: `pytest tests/test_us4_guardrails.py` passes.

- [X] T045 [P] [US4] Implement `src/reminder_agent/guard.py`: detect the marker, any 40-char whitespace-normalised run of the system text, or any `secrets` value in any string field (research R7)
- [X] T046 [US4] Extend `src/reminder_agent/agent.py`: refuse branch (reason kept, others null); run `guard.py` on every final output and replace a hit with `refuse`/`prompt_extraction`
- [X] T047 [US4] Extend `prompts/system.md` with scope (FR-013), the three reasons and precedence (FR-014..FR-016, including "real reminder + attack → refuse"), quoted-content-is-data (FR-017), never reveal instructions, and do-not-refuse harmless wording (PROP-005)
- [ ] T048 [US4] Run `pytest tests/test_us4_guardrails.py` and all earlier story tests → green

---

## Phase 9: User Story 3 — Reschedule or snooze (Priority: P2)

**Goal**: Referenced reminders move to a new time or snooze for N minutes.

**Independent Test**: `pytest tests/test_us3_reschedule_snooze.py` passes.

- [X] T049 [US3] Extend `src/reminder_agent/resolve.py` and `agent.py`: reschedule (requires data-model.md Interpretation.reminder_ref and a resolvable future due; past → clarify) and snooze (requires reminder_ref and data-model.md Interpretation.snooze_minutes ≥ 1; `due` null), else clarify per FR-012
- [X] T050 [US3] Extend `prompts/system.md` with reschedule/snooze rules (reference copied as written, hours → minutes, no reference → clarify)
- [ ] T051 [US3] Run full `pytest` → green; `coverage report` ≥ 90%

---

## Phase 10: First Generation and Bounded Repair (Principle XI)

- [ ] T052 Run `bash .harness/gates.sh` (G1–G9 with the real Gemini key); save the report in `reports/`
- [ ] T053 Commit the implementation and its first harness report unchanged; tag `gen-1b-first-generation`
- [ ] T054 If any gate is red: at most two commits `repair(1/2): …` / `repair(2/2): …` touching only `src/` and `prompts/`, re-running `bash .harness/gates.sh` after each; if still red after attempt 2, stop and open a human review

---

## Phase 11: Polish & Cross-Cutting Concerns

- [ ] T055 [P] Create `CLAUDE.md` (< 200 lines: build/test/run commands from quickstart.md, module map from plan.md, conventions: ID scheme, protected paths, repair rule) — org policy
- [ ] T056 [P] Create `README.md` summarising purpose, setup, the latest harness verdict and links to spec/plan/reports
- [ ] T057 Run quickstart.md §2–§5 end to end and confirm each expected outcome

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (1) → Foundational (2) → US5 harness (3) → Story tests (4) → **Baseline tag (5)** → US1 (6) → US2 (7) → US4 (8) → US3 (9) → First generation/repair (10) → Polish (11). T055 may be done any time.
- Phases 2–4 are protected; nothing in them may change after T030 without a spec amendment and a new baseline tag.

### User Story Dependencies

- **US5** (harness) has no dependency on agent code; it is built first because Principle VIII requires it before implementation.
- **US1** depends only on Phase 5. It is the MVP.
- **US2, US4, US3** each extend `resolve.py`/`agent.py`/`prompts/system.md` built in US1, so they run after US1 and in this order (same files, not parallel). Each remains independently testable through its own test file.

### Within Each Story

- Tests written in Phase 4 and observed failing in T028 before any implementation task.
- Data types (request, interpretation, output) before resolution, before orchestration, before CLI.

### Parallel Opportunities

- Phase 1: T003, T004, T005.
- Phase 2: T007, T008, T010, T012 together; T009 after T007 (expected objects validated against the schema).
- Phase 4: T018–T026 are all separate files and run in parallel.
- Phase 6: T031, T032, T033, T034 in parallel; then T035 → T036 → T037 → T038 → T039.
- Phase 8: T045 in parallel with T047.

---

## Parallel Example: Phase 4 (story tests)

```bash
Task: "Write tests/test_us1_create.py"
Task: "Write tests/test_us2_clarify.py"
Task: "Write tests/test_us3_reschedule_snooze.py"
Task: "Write tests/test_us4_guardrails.py"
Task: "Write tests/test_model_client.py"
Task: "Write tests/test_interpretation.py"
```

## Parallel Example: User Story 1

```bash
Task: "Implement src/reminder_agent/request.py"
Task: "Implement src/reminder_agent/calendar_facts.py"
Task: "Implement src/reminder_agent/model_client.py"
Task: "Implement src/reminder_agent/interpretation.py"
```

---

## Implementation Strategy

### MVP First

1. Phases 1–5: protected assets, red run, human approval, baseline tag.
2. Phase 6 (US1): create works with the fake client; one real CLI call (quickstart.md §3–§4).
3. **Stop and validate** before extending.

### Incremental Delivery

US2 (clarify) → US4 (guardrails) → US3 (reschedule/snooze), each closed by its own test file
plus all earlier ones. Only then the full G9 run, first-generation tag and bounded repair.

---

## Notes

- [P] = different files, no dependency on an incomplete task.
- The harness and tests are never edited to make the agent pass (G1).
- Commit after each task or logical group; implementation commits touch only `src/` and `prompts/`.
