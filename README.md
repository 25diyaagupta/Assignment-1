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

# AI Use Statement

- **Tools used:** Claude Code for code generation and implementation support; Claude Chat for guidance and clarification; Git for version control; and the project's test, linting, coverage, and evaluation harness tools to verify the implementation.

- **Coding agent:** Claude Code was asked to implement Part 1A (the deterministic tiered token-bucket limiter) and Part 1B (the natural-language reminder agent). It worked from the approved specifications, constitution, implementation plan, task lists, tests, and harness/evaluation configuration. The implementation was checked against the defined requirements and acceptance criteria.

- **What I did myself:** I reviewed and approved the constitution, specifications, plans, tasks, tests, and evaluation criteria. I reviewed the generated implementation and test results, examined failures and repair evidence, and decided whether the changes were acceptable. I also approved the baseline tags and made the final ACCEPT decision based on the harness results.

- **Mentor / chat use:** I used Claude Chat to understand the assignment requirements, clarify technical concepts, troubleshoot errors, interpret test and evaluation results, and understand the failures and repairs. It was used as a support tool rather than as a replacement for reviewing and making my own decisions.

- **Logs and reflection:** I wrote the harness logs and reflection myself. AI helped me understand and verify technical facts, test results, and evidence, but did not write or make the final decisions in my logs or reflection.