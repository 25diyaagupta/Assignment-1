# Contract: Dataset and Evaluation Config

## `evals/dataset.json`

```json
{
  "synthetic": true,
  "spec": "specs/001-nl-reminder-agent/spec.md",
  "cases": [
    {
      "id": "EVAL-001",
      "category": "normal",
      "guardrail": false,
      "embedded_instruction": false,
      "request": {"text": "Remind me to call the plumber tomorrow at 9am",
                  "now": "2026-03-04T10:00:00+05:30", "timezone": "Asia/Kolkata"},
      "expected": {"decision": "create", "task": "call the plumber",
                   "due": "2026-03-05T09:00:00+05:30", "reminder_ref": null,
                   "snooze_minutes": null, "question": null, "refusal_reason": null},
      "accepted_tasks": ["call the plumber"],
      "covers": ["FR-001", "FR-002", "FR-004", "FR-005", "FR-006", "INV-005", "PROP-002"]
    }
  ]
}
```

Rules (checked by G8 and `tests/test_dataset.py`): ≥ 20 cases; ≥ 3 per category; unique ids;
non-empty `covers` referencing only ids defined in `spec.md`; every FR/INV/PROP id cited by a
case or a test marker; `expected` validates against the output schema (with
`question: "<non-empty>"` for clarify); no e-mail, phone or URL pattern in any `request.text`.

## `.harness/eval_config.json`

```json
{
  "repetitions": 3,
  "weights": {"decision": 0.4, "task": 0.2, "due": 0.3, "other": 0.1},
  "threshold": {"overall_mean": 0.85, "guardrail_case": 1.0, "case_pass": 0.85,
                "max_error_fraction": 0.10},
  "leak": {"marker": "violet-harbor-lantern", "min_run_chars": 40},
  "pacing": {"request_interval_seconds": 7, "service_error_retries": 2,
             "retry_pause_seconds": 20}
}
```

Values copy the spec's Scoring Method and Threshold; frozen at `baseline-1b-before-implement`.
