# Part-1A: Tiered token-bucket rate limiter

A Python 3.12 library (`tiered_limiter`) that limits requests per client key with token
buckets grouped into tiers (a tier can have several limits). Time comes from an injected
clock. A separate function maps each decision to an HTTP outcome: `200`, or `429` with a
`Retry-After` header. No runtime dependencies.

Specification and design: [`specs/001-tiered-rate-limiter/`](specs/001-tiered-rate-limiter/).

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

## Run the harness

```bash
.harness/run.sh
```

It runs gates G1–G6, then the G7 self-check, and stops at the first failure. It prints
`ALL GATES PASSED` and exits 0 only when every gate passes. No gate uses the network, so
this harness has no `--offline` option.

| Gate | Check |
|---|---|
| G1 Integrity | `tests/` and `.harness/` unchanged since tag `harness-approved` |
| G2 Suppressions | no suppression comments in `*.py` |
| G3 Lint/format | `ruff check` and `ruff format --check` |
| G4 Security | `bandit` over `src/` |
| G5 Tests | `pytest` with branch coverage ≥ 90% |
| G6 Secrets | `detect-secrets` over the project files |
| G7 Self-check | each gate must fail on a deliberately broken fake (`.harness/self_check.sh`) |

## Folder layout

```text
Part-1A/
├── src/tiered_limiter/   # the library
├── tests/                # pytest suite (protected after tag harness-approved)
├── .harness/             # run.sh, gates.sh, self_check.sh (protected)
├── specs/001-tiered-rate-limiter/   # spec, plan, tasks, contracts
├── evidence/             # harness runs and generations (see below)
├── pyproject.toml
└── requirements-dev.txt
```

## Evidence

[`evidence/`](evidence/) holds the record of the build:

- `initial-generation/`, `final-generation/`: copies of `src/` before and after repair
- `repair-1/`: the failure that triggered the repair
- `harness-results/`: saved harness runs (`run-1.txt` …)
- `harness-log.md`: log of the harness runs
