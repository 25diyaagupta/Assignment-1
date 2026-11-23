# Assignment-1

Two small Python projects built with Spec Kit (spec → plan → tasks → implement), each
guarded by its own quality-gate harness.

| Folder | What it contains |
|---|---|
| [`Part-1A/`](Part-1A/README.md) | Tiered token-bucket rate limiter (library plus an HTTP 200/429 mapping) and its harness |
| [`Part-1B/`](Part-1B/README.md) | Natural-language reminder agent (Gemini via REST) with a three-layer evaluation harness |

Each part has its own `specs/`, `src/`, `tests/`, `.harness/` and `evidence/` folders and
its own virtual environment. Run every command from inside the part's folder.

## Setup environment

- Ubuntu 22.04
- Python 3.12, installed and managed with `uv`
- Spec Kit CLI 1.4.3 (`specify`)
- Claude Code

## AI use

AI-USE STATEMENT: to be written by the student
