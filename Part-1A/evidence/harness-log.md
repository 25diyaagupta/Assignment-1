# Part 1A harness log

## 1. First generation

The agent received the approved specification covering AC-001 to AC-036, along with the implementation plan, task list, constitution v1.0.2, and protected tests.

Before implementation and before any actual harness run, the baseline tags `baseline-1a-before-implement` and `harness-approved` were created. The first generated version of the source code was saved unchanged under `evidence/initial-generation/src/`.

The initial-generation snapshot was committed as A6 (`[insert the full commit hash from Step 1]`). This preserves the original output so that it can be compared with the repaired implementation.

## 2. Harness runs

### run-1

The first run stopped at G3 because the `src/` directory did not exist yet. This happened because the harness was run before the initial source generation was available.

This was a setup-order mistake, not a development failure. Therefore, run-1 was not treated as a repair cycle.

### run-2

G1 and G2 passed, but G3 failed because Ruff reported a formatting issue at:

`src/tiered_limiter/_validate.py:129`

The finding was limited to formatting. The first 40 lines of the run-2 output were saved in `evidence/repair-1/failure-evidence.txt` and used as evidence for the repair.

### run-3

After the formatting repair, the harness was run again. All seven gates passed.

## 3. Failure and repair

The evidence provided to the agent was the first 40 lines of run-2, saved in `evidence/repair-1/failure-evidence.txt`.

The repair instruction was deliberately restricted:

- Change files under `src/` only.
- Preserve the existing behaviour.
- Do not add suppressions or weaken checks.
- Do not modify `tests/` or `.harness/`.

Only `src/tiered_limiter/_validate.py` was changed. The change was small: one string was joined onto a single line, resulting in a diff of one insertion and two deletions (+1/−2).

I checked the repair scope using `git diff`. It showed no changes under `tests/` or `.harness/`. G1 integrity also passed on the subsequent run.

The failure was a formatting finding, not a functional defect. The repair addressed that finding without changing the tests or harness configuration. All seven gates passed on run-3.

## 4. Final result

The final run passed all seven harness gates.

- **Tests:** 127 passed, based on 42 test functions.
- **Coverage:** 96%, against the required threshold of 90%.
- **G5 duration:** 4.21 seconds.
- **G7 self-check:** The self-check demonstrated that every gate fails when given its corresponding broken fake.

The final result therefore met the reported test and coverage requirements, and the harness self-check behaved as expected.

## 5. Decision, limitations, disclosures

### Decision

**Pending final source-code review.**

Before deciding ACCEPT or REJECT, I still need to inspect `src/tiered_limiter/limiter.py` and `src/tiered_limiter/http_mapping.py`.

The review must confirm:

- `Retry-After` is calculated using ceiling (`ceil`) and has a minimum value of 1.
- No `float` is used in the relevant implementation.

After checking these files, I will record the final decision and explain whether the implementation satisfies the specification and the relevant requirements.

### Known limitations and scope decisions

- The following lines remained uncovered: `_validate.py` lines 120–121, `clock.py` line 34, and `limiter.py` lines 56–57 and 59–60.
- The limiter is not thread-safe by design, as documented in FR-012.
- The lean scope amendment v1.0.2 was made before any harness run. As a result, the project does not include a benchmark, history secret scan, reverse-order hook, or SC-004 and SC-005 checks.
- The secret scan covers project files only. The `.specify/` directory contains Spec Kit SHA-256 hashes, which is why it is excluded from that scan.
- A throwaway limiter was created outside the repository to check that the tests could detect a broken implementation. It was deleted afterwards.

### Disclosures

The first run stopped because the source directory was not yet available; this was a setup-order issue rather than a development failure. The only repair required by the subsequent run was a small formatting correction in `_validate.py`.

The final result demonstrates that the defined seven-gate harness passed for this implementation. It does not establish that the implementation is thread-safe or that it has been benchmarked, since those were outside the agreed scope.