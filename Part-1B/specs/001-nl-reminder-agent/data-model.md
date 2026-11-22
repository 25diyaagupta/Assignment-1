# Data Model: Natural-Language Reminder Agent

## Request (input; FR-001, FR-003)

| Field | Type | Rule |
|---|---|---|
| `text` | string | Any string, including empty (empty → `clarify`, FR-007). |
| `now` | string | ISO 8601 datetime **with** UTC offset; naive or unparseable → `InvalidRequest`. |
| `timezone` | string | IANA name loadable by `zoneinfo`; unknown → `InvalidRequest`. |

Validation happens before any model call. `now` is converted to the request timezone for all
local-date reasoning.

## CalendarFacts (derived, internal)

Computed by `calendar_facts.py` from `now` and `timezone` only: local date and time, weekday
name, current UTC offset, and the 14 following dates each with its weekday name. Serialised into
the user message so the model chooses dates, never computes them.

## Interpretation (model reply, internal)

| Field | Type | Notes |
|---|---|---|
| `decision` | enum | `create`, `reschedule`, `snooze`, `clarify`, `refuse` |
| `task` | string \| null | |
| `due_local` | string \| null | `YYYY-MM-DDTHH:MM`, local wall time in the request timezone |
| `relative_minutes` | int \| null | ≥ 0; set only for duration phrases ("in 45 minutes") |
| `reminder_ref` | string \| null | |
| `snooze_minutes` | int \| null | ≥ 1 |
| `question` | string \| null | |
| `refusal_reason` | enum \| null | `out_of_scope`, `instruction_override`, `prompt_extraction` |

Rules: at most one of `due_local` / `relative_minutes` is non-null; unknown keys, wrong types or
values outside an enum → `InvalidModelOutput`.

## DecisionOutput (public output; FR-002, Output Schema)

Seven keys, always present: `decision`, `task`, `due`, `reminder_ref`, `snooze_minutes`,
`question`, `refusal_reason`. Per-decision required/null rules are exactly the spec's Output
Schema table. `due` is serialised as `YYYY-MM-DDTHH:MM:SS±HH:MM` in the request timezone.

### Resolution transitions (Interpretation → DecisionOutput)

```text
refuse            → refuse (reason kept; all else null)
clarify           → clarify (question kept, default text if empty; all else null)
snooze            → snooze if reminder_ref and snooze_minutes ≥ 1, else clarify
create/reschedule → compute due:
                      relative_minutes → now + minutes
                      due_local        → attach tz; gap or overlap → clarify
                      neither          → clarify (time missing)
                    due < now          → clarify (INV-006)
                    create w/o task    → clarify; reschedule w/o reminder_ref → clarify
                    otherwise          → create / reschedule
any               → leak guard hit     → refuse / prompt_extraction
```

Fields not applicable to the final decision are forced to `null`.

## Errors

| Type | Raised by | Meaning |
|---|---|---|
| `InvalidRequest` | `request.py` | Bad `now`/`timezone` (FR-003); no model call. |
| `ModelTimeout`, `ModelRateLimited`, `ModelUnavailable` | `model_client.py` | Service errors (harness `error`). |
| `ModelConfigError` | `model_client.py` | Missing key, 400/401/403/404; harness aborts. |
| `InvalidModelOutput` | `interpretation.py` | Model answered with unusable text (harness `fail`). |

## EvalCase (`evals/dataset.json`; FR-025)

| Field | Type | Notes |
|---|---|---|
| `id` | string | `EVAL-nnn`, unique |
| `category` | enum | `normal`, `boundary`, `ambiguous`, `missing_information`, `malformed`, `adversarial` |
| `guardrail` | bool | true for expected `refuse` and for embedded-instruction cases |
| `embedded_instruction` | bool | marks PROP-003 cases |
| `request` | Request | |
| `expected` | DecisionOutput | `question` holds `"<non-empty>"` placeholder for clarify; never compared verbatim |
| `accepted_tasks` | string[] | normalised-match variants; empty when expected task is null |
| `covers` | string[] | non-empty; FR/INV/PROP ids defined in spec.md |

## RepetitionResult / CaseResult / RunReport (harness)

- **RepetitionResult**: `rep` (1–3), `outcome` (`ok` \| `error`), raw output text, `l1_pass`,
  failed INV/PROP ids, component scores (decision, task, due, other), weighted score.
- **CaseResult**: case id, three RepetitionResults, `score` (0 if any rep failed INV/PROP;
  mean otherwise), `outcome` (`pass` \| `fail` \| `error`), `guardrail`.
- **RunReport**: timestamp of the run (harness-side, not agent), model id, counts of
  `pass`/`fail`/`error`, overall mean over non-error cases, each threshold condition with
  true/false, final verdict. Never contains the API key or request headers.
