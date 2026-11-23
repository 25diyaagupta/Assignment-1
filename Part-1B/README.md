# Part-1B: Natural-language reminder agent

A Python 3.12 package (`reminder_agent`) that takes free text plus a supplied `now`
(ISO 8601 with offset) and an IANA `timezone`, and returns one JSON decision:
`create`, `reschedule`, `snooze`, `clarify` or `refuse`. Google Gemini, called over its
REST API from the single module `src/reminder_agent/model_client.py`, interprets the
language. All date arithmetic, validation and the leak guard are plain code. No runtime
dependencies beyond the standard library.

Specification and design: [`specs/001-nl-reminder-agent/`](specs/001-nl-reminder-agent/).

## Install

From this folder:

```bash
uv venv --python 3.12 .venv
. .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install -e .
```

If `uv` fails with `invalid peer certificate: UnknownIssuer`, add `--system-certs` to the
`uv pip install` commands.

## API key

The key goes only in `.env`, which is listed in `.gitignore` and must never be committed:

```bash
cp .env.example .env
```

Then fill in `.env`:

| Variable | Meaning |
|---|---|
| `GEMINI_API_KEY` | required for the live evaluation (G9) and the CLI |
| `GEMINI_MODEL` | optional, default `gemini-2.5-flash` |
| `GEMINI_TIMEOUT_SECONDS` | optional, default `30` |

## Run the harness

```bash
bash .harness/gates.sh --offline   # G1–G8 and the self-check; no network, no key
bash .harness/gates.sh             # same, plus G9: live evaluation with Gemini
```

It exits 0 only when every gate that ran passed.

| Gate | Check |
|---|---|
| G1 Integrity | `evals/dataset.json`, `.harness/`, `tests/` unchanged since tag `baseline-1b-before-implement` |
| G2 Suppressions | no suppression comments in `*.py` |
| G3 Lint/format | `ruff check` and `ruff format --check` over `src`, `tests`, `.harness` |
| G4 Security | `bandit` over `src` and `.harness` |
| G5 Tests | `pytest` with a fake model client, network blocked; coverage ≥ 90% |
| G6 Secrets | `.env` untracked; `detect-secrets` over the project files |
| G7 Clock | no wall-clock calls in `src/` or `prompts/` |
| G8 Dataset | dataset shape, ID traceability, no e-mail/phone/URL in inputs |
| Self-check | fake apps that each break one evaluation layer must be caught |
| G9 Evaluation | 30 cases × 3 repetitions; pass needs mean ≥ 0.85, every guardrail case = 1.0, structure clean, errors within cap |

G9 writes its report to `reports/`.

One request from the command line (needs the key in the environment):

```bash
echo '{"text":"Remind me to call the plumber tomorrow at 9am","now":"2026-03-04T10:00:00+05:30","timezone":"Asia/Kolkata"}' \
  | python -m reminder_agent
```

## Folder layout

```text
Part-1B/
├── src/reminder_agent/   # the agent; model_client.py is the only network module
├── prompts/system.md     # system instructions for the model
├── tests/                # pytest suite (protected)
├── evals/dataset.json    # 30 synthetic evaluation cases (protected)
├── .harness/             # gates.sh, evaluate.py, scoring.py, self_check.py, check_dataset.py,
│                         # output.schema.json, eval_config.json (protected)
├── reports/              # evaluation reports written by G9
├── specs/001-nl-reminder-agent/   # spec, plan, tasks, contracts
├── evidence/             # harness runs, evaluations and repairs (see below)
├── .env.example          # variable names only; copy to .env
├── pyproject.toml
└── requirements-dev.txt
```

## Evidence

[`evidence/`](evidence/) holds the record of the build:

- `eval-run-1/`, `eval-run-2/`: live evaluation reports (JSON and Markdown)
- `eval-results.json`: evaluation results
- `repair-1/`, `repair-2/`: the failure evidence behind each repair
- `final-generation/`: copies of `src/` and `prompts/` after repair
- `harness-results/`: saved harness runs (`run-1.txt` …)
- `harness-log.md`: log of the harness runs
