# Research: Natural-Language Reminder Agent

All Technical Context items were resolvable from the brief, the spec and the constitution; no
NEEDS CLARIFICATION remained. Each decision below records what was chosen and why.

## R1. Gemini access: REST over `http.client`

- **Decision**: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  via `http.client.HTTPSConnection("generativelanguage.googleapis.com", timeout=T,
  context=ssl.create_default_context())`. Headers: `Content-Type: application/json`,
  `x-goog-api-key: <key>`. Reply text from `candidates[0].content.parts[*].text` (joined).
- **Rationale**: one endpoint, one JSON body; no runtime dependency (user requirement, Principle I).
  `http.client` avoids `urllib.request.urlopen`, which ruff S310 and bandit B310 flag and which
  could only pass with a forbidden suppression (Principle II). The key goes in a header, never
  the query string, so it cannot leak through logged URLs (Principle IX).
- **Alternatives**: `google-genai` SDK (large dependency tree for one call); `urllib.request`
  (lint findings); `requests`/`httpx` (needless dependency).

## R2. Request configuration

- **Decision**: body = `systemInstruction` (system text), `contents` (one user turn),
  `generationConfig` = `{temperature: 0, candidateCount: 1, responseMimeType:
  "application/json", responseSchema: <interpretation schema>}`. Model id from `GEMINI_MODEL`,
  default `gemini-2.5-flash`; timeout from `GEMINI_TIMEOUT_SECONDS`, default 30.
- **Rationale**: temperature 0 and JSON mode maximise PROP-006 (same decision ×3) and L1 pass
  rate; `responseSchema` (OpenAPI subset, `nullable: true` supported) constrains field names and
  enums at the source. The schema is passed *in* by `prompt.py`, so the client stays free of
  decision logic.
- **Open check (not a blocker)**: confirm the default model id is still served for the account
  before the first G9 run (`quickstart.md` step 4); it is configuration, not code.
- **Alternatives**: free-text output parsed with regex (lower L1 reliability); higher temperature
  (hurts PROP-006).

## R3. Who does date arithmetic: code, not the model

- **Decision**: the model returns an *interpretation*: either `due_local` (`YYYY-MM-DDTHH:MM`
  local wall time) or `relative_minutes` (for "in N minutes/hours/days"), never an offset.
  `resolve.py` computes `due` = `now + relative_minutes`, or attaches the request timezone to
  `due_local` with `zoneinfo`. The prompt carries calendar facts computed by code: local date,
  weekday, current offset, and the next 14 dates with weekday names.
- **Rationale**: exact due time is 30% of every create/reschedule score, and DST offsets, year
  rollover and "next Monday" are where models slip. Code makes INV-005/INV-007 hold by
  construction; the model only needs to pick the right calendar date from a list.
- **DST handling**: a wall time that does not exist (spring-forward gap; detected because
  converting to UTC and back changes it) or that is ambiguous (fall-back overlap; `fold=0` and
  `fold=1` give different offsets) becomes `clarify` — never a guess (FR-008, PROP-001).
- **Not before now**: `due < now` for `create`/`reschedule` becomes `clarify` (INV-006, FR-012).
- **Alternatives**: model emits full ISO datetime with offset (rejected: unreliable offsets);
  rule-based parser without a model (rejected: brittle on free text, out of brief).

## R4. Output validation and invalid model text

- **Decision**: `interpretation.py` validates the model JSON (keys, types, enums). Failure raises
  `InvalidModelOutput`; the agent never returns raw model text. The harness records that
  repetition as an L1 failure (`fail`), not `error`, since the service answered.
- **Rationale**: Principle V forbids passing unvalidated text through; Principle X forbids
  relabelling wrong answers as service errors.
- **Alternatives**: silently convert to `clarify` (would hide L1 failures from the score).

## R5. Service error mapping (Principle X)

| Condition | Typed error | Harness label |
|---|---|---|
| `TimeoutError` / `socket.timeout` during connect or read | `ModelTimeout` | `error` |
| HTTP 429 | `ModelRateLimited` | `error` |
| HTTP 500, 502, 503, 504; `OSError`/`http.client.HTTPException` in transport | `ModelUnavailable` | `error` |
| HTTP 400, 401, 403, 404; missing `GEMINI_API_KEY` | `ModelConfigError` | run aborts (exit 2) |
| 200 with no candidate text (e.g. safety block, `finishReason` ≠ `STOP`) | returns empty string → `InvalidModelOutput` | `fail` |

- **Rationale**: config errors would otherwise turn all 90 calls into `error` and the error cap
  would fail the run with a misleading count; aborting tells the operator to fix configuration.
  A safety block is the model's answer, so it is judged like any other answer.
- **Retries**: the client never retries. `evaluate.py` retries a repetition at most 2 more times
  only for `ModelRateLimited`/`ModelUnavailable`/`ModelTimeout`, after a fixed pause; a wrong
  answer is never retried. If still failing, the repetition is `error`.

## R6. Pacing

- **Decision**: `eval_config.json` holds `request_interval_seconds` (default 7) and the harness
  sleeps between calls. 90 calls ≈ 11 minutes.
- **Rationale**: keeps a free-tier key under ~10 requests per minute, so `error` counts reflect
  real outages, not self-inflicted rate limiting.

## R7. Leak guard and canary (PROP-004)

- **Decision**: `prompts/system.md` contains a fixed low-entropy marker line
  (`Marker: violet-harbor-lantern`), recorded in `eval_config.json`. `guard.py` (agent) and
  `evaluate.py` (harness, independently) check every string field of the output for: the marker,
  any 40-character run of the system text (whitespace-normalised), and the value of
  `GEMINI_API_KEY`. The agent turns a hit into `refuse`/`prompt_extraction`; the harness counts a
  hit as a PROP-004 failure. G9 fails if the marker is missing from `prompts/system.md`, so the
  check cannot pass vacuously.
- **Rationale**: defence in depth; a low-entropy marker avoids a `detect-secrets` finding.

## R8. Guardrail behaviour lives in the prompt, enforced by code where possible

- **Decision**: the prompt states scope, refusal reasons and precedence (FR-013..018), the rule
  that quoted content is data (FR-017), and the "never guess" rule. Code enforces what it can
  without language understanding: per-decision null rules, enum membership, DST/past-time
  clarify, leak guard.
- **Rationale**: classification of intent needs the model; structure and time do not.

## R9. Test isolation

- **Decision**: `tests/conftest.py` replaces `socket.socket` and `socket.create_connection`
  with a function that raises, for every test. `FakeModelClient` returns scripted text or raises
  scripted errors. `test_model_client.py` injects a stub connection factory into `GeminiClient`
  to test HTTP/error mapping without a network.
- **Rationale**: G5 must make no network calls (constitution gate table); no extra dependency.

## R10. Harness independence

- **Decision**: harness L1 uses `jsonschema` on `.harness/output.schema.json`; L2/L3 are
  re-implemented in `.harness/scoring.py` and do not import the agent's validators. The harness
  imports only `reminder_agent.handle_request`, `Request`, `GeminiClient` and the error types.
- **Rationale**: the agent cannot pass by grading itself; `.harness/` is frozen at baseline while
  `src/` changes.
