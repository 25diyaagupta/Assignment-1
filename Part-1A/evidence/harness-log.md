# Part 1A harness log

## 1. First generation

- Input provided to the agent: approved specification (AC-001 to AC-036), plan, tasks, constitution v1.0.2 and protected tests.
- Baseline tags created before generation: `baseline-1a-before-implement` and `harness-approved`.
- First generated source saved unchanged in `evidence/initial-generation/src/`.
- Snapshot saved in commit A6.

## 2. Harness runs

### run-1

- Harness stopped at G3.
- The `src/` directory did not exist when the run started.
- This was caused by the order of setup steps. It was not a code defect or a repair cycle.

### run-2

- G1 and G2 passed.
- G3 failed because Ruff reported a formatting issue.
- File: `src/tiered_limiter/_validate.py`
- Location: line 129.
- First 40 lines of the run output saved in `evidence/repair-1/failure-evidence.txt`.

### run-3

- Run completed successfully.
- All seven gates passed.

## 3. Failure and repair

- Evidence used: first 40 lines of run-2, saved in `evidence/repair-1/failure-evidence.txt`.
- Repair scope: files under `src/` only.
- Requirements given to the agent: preserve behaviour, do not add suppressions, and do not modify `tests/` or `.harness/`.
- Only `_validate.py` changed.
- Diff: one insertion and two deletions (+1/−2). A string was joined onto one line to fix the formatting issue.
- `git diff` showed no changes under `tests/` or `.harness/`.
- G1 integrity passed after the repair.
- The repair addressed a formatting issue; it did not change the intended behaviour or weaken the checks.

## 4. Final result

- All seven gates passed in run-3.
- Tests: 127 passed, from 42 test functions.
- Coverage: 96%.
- Required coverage threshold: 90%.
- G5 execution time: 4.21 seconds.
- G7 self-check: every gate failed when tested with its corresponding broken fake.

## 5. Decision, limitations, disclosures

### Decision: ACCEPT

The final implementation is accepted against the defined Part 1A checks.

Reasons:
- All seven gates passed.
- 127 tests passed.
- Coverage reached 96%, above the 90% threshold.
- G7 detected the broken fake for every gate.
- The code review of `http_mapping.py` found `max(1, ceil(retry_after))` in the `Retry-After` calculation at line 38. This rounds the value up and enforces a minimum of one second.
- The grep check found no `float` matches in `http_mapping.py` or `limiter.py`.

### Known limitations

- Uncovered lines: `_validate.py` 120–121, `clock.py` 34, and `limiter.py` 56–57 and 59–60.
- The limiter is not thread-safe by design, as specified in FR-012.
- The lean scope amendment v1.0.2 was made before the first run.
- No benchmark, history secret scan, reverse-order hook, SC-004 or SC-005 checks were included.
- The secret scan covers project files only. `.specify/` contains Spec Kit SHA-256 hashes and is excluded from the scan.
- A throwaway limiter was created outside the repository to check that the tests could detect a broken implementation. It was deleted afterwards.

### Disclosures

- The first run stopped because the source directory was not present yet.
- The only repair was a small formatting correction in `_validate.py`.
- The final result applies to the implemented scope and the seven gates defined for this assignment. It does not establish thread safety or benchmark performance.