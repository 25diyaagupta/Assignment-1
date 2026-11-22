# Part 1A harness log

## 1. First generation
Input: approved spec (AC-001 to AC-036), plan, tasks, constitution v1.0.2, protected tests
Saved in evidence/initial-generation/src/ before any real harness run
Commit message "A6", with the hash you noted
Baseline tags baseline-1a-before-implement and harness-approved were created before generation

## 2. Harness runs
### run-1
stopped at G3, src/ did not exist yet (generation had not run). Setup order issue.
### run-2
G1 and G2 passed, G3 failed with a ruff format finding at src/tiered_limiter/_validate.py:129
### run-3
run-3: all 7 gates passed

## 3. Failure and repair
Evidence given to the agent: first 40 lines of run-2 in evidence/repair-1/failure-evidence.txt
Instruction: repair src/ only, keep behaviour, no suppressions, don't touch tests/ or .harness/
Change: _validate.py only (+1/−2), a string reformatted onto one line
Same gates re-run in full: all passed
Weakening check: git diff showed nothing under tests/ or .harness/, and the G1 integrity gate passed

## 4. Final result
127 test cases passed (from 42 test functions)
Coverage 96% against a 90% threshold
G5 wall time 4.21 s
G7 self-check: each gate fails on its broken fake and passes on a clean one

## 5. Decision, limitations, disclosures
Uncovered lines: _validate.py 120-121, clock.py 34, limiter.py 56-57 and 59-60
Not thread-safe by design (FR-012)
Scope was cut before any run (lean amendment v1.0.2): no bench, no history secret scan, no reverse-order hook, no SC-004 or SC-005 checks
.specify/ is excluded from the secret scan because of SHA-256 hashes in Spec Kit files
A throwaway limiter was written outside the repo to check the tests could catch a broken one, then deleted
ACCEPT or REJECT, and the reason, are yours. Read limiter.py and http_mapping.py first. Check that Retry-After uses ceil with a minimum of 1 and that no float is used.