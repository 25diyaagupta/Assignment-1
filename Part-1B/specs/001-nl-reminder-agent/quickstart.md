# Quickstart: Natural-Language Reminder Agent

Run from the `Part-1B/` repository root.

## 1. Environment

```bash
uv venv --python 3.12 .venv
. .venv/bin/activate
uv pip install -e . -r requirements-dev.txt
cp .env.example .env          # then put your key in GEMINI_API_KEY; .env is git-ignored
```

`.env` variables: `GEMINI_API_KEY` (required for G9 and the CLI), `GEMINI_MODEL` (optional,
default `gemini-2.5-flash`), `GEMINI_TIMEOUT_SECONDS` (optional, default 30).

## 2. Offline checks (no key, no network)

```bash
pytest                      # G5 alone; expected: all pass, network blocked by conftest
bash .harness/gates.sh --offline   # G1–G8; expected: every gate PASS, exit 0
```

Before implementation (after the tests are written) `pytest` is expected to fail: that is the
red step required before tagging `baseline-1b-before-implement`.

## 3. One request through the CLI

```bash
echo '{"text":"Remind me to call the plumber tomorrow at 9am",
       "now":"2026-03-04T10:00:00+05:30","timezone":"Asia/Kolkata"}' \
  | python -m reminder_agent
```

Expected: one object with `"decision": "create"`, `"task": "call the plumber"`,
`"due": "2026-03-05T09:00:00+05:30"` and the other four keys `null`
(see [contracts/agent-api.md](contracts/agent-api.md)).

## 4. Confirm the model id

The first CLI call in step 3 confirms that `GEMINI_MODEL` is served for the key. A
`ModelConfigError` (exit 2) with status 404 means the model id must be changed in `.env`.

## 5. Full evaluation (G9)

```bash
bash .harness/gates.sh      # G1–G9; G9 makes 90 paced model calls (~11 minutes)
```

Expected outcome: report written to `reports/` with per-case scores, `pass`/`fail`/`error`
counts and each threshold condition; exit 0 only when overall mean ≥ 0.85, every guardrail case
= 1.0, L1 clean in every non-error repetition, no guardrail `error`, and ≤ 10% `error` cases
(spec §Threshold; config in [contracts/dataset-format.md](contracts/dataset-format.md)).

## 6. Validation scenarios mapped to the spec

| Scenario | How to see it | Spec |
|---|---|---|
| Create with DST offset | EVAL-008 row in the report: due `2026-03-08T10:00:00-04:00` | FR-006, INV-007 |
| Clarify, never guess | EVAL-014..019 rows: `clarify`, `task`/`due` null | PROP-001 |
| Past-time reschedule | EVAL-030: `clarify` | FR-012, INV-006 |
| Guardrails exact | EVAL-023..027, 029 each score 1.0 | FR-013..018 |
| Service error kept apart | `tests/test_us5_scoring.py` scripted timeout → `error`, excluded from mean | FR-022 |
| Bad request context | `tests/test_request_validation.py`: no model call, `InvalidRequest` | FR-003 |
