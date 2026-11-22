#!/usr/bin/env bash
# Quality gates G1-G9 (constitution §Quality Gates, plan.md §Harness Gates).
# Usage: bash .harness/gates.sh [--offline]
#   --offline runs G1-G8 and the harness self-check only: no network, no key.
# Exits 0 only when every gate that ran passed.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2
PY="${PYTHON:-python}"
TAG="baseline-1b-before-implement"
OFFLINE=0
[[ "${1:-}" == "--offline" ]] && OFFLINE=1
FAILED=0

gate() {
  local name="$1"
  shift
  if "$@"; then
    echo "PASS $name"
  else
    echo "FAIL $name"
    FAILED=1
  fi
}

existing() {
  local path
  for path in "$@"; do
    [[ -e "$path" ]] && printf '%s\n' "$path"
  done
}

g1_integrity() {
  if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
    echo "WARN G1: tag $TAG does not exist yet; integrity not enforced"
    return 0
  fi
  local changed untracked
  changed="$(git diff --name-only "$TAG" -- evals/dataset.json .harness tests)"
  untracked="$(git ls-files --others --exclude-standard -- evals/dataset.json .harness tests)"
  if [[ -n "$changed$untracked" ]]; then
    printf 'G1: protected paths changed since %s:\n%s\n%s\n' "$TAG" "$changed" "$untracked"
    return 1
  fi
}

g2_suppressions() {
  local pattern='#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no cover|fmt:\s*off)'
  rg -n --glob '*.py' "$pattern" .
  [[ $? -eq 1 ]]
}

g3_lint() {
  mapfile -t paths < <(existing src tests .harness)
  ruff check "${paths[@]}" && ruff format --check "${paths[@]}"
}

g4_security() {
  mapfile -t paths < <(existing src .harness)
  bandit -q -r "${paths[@]}"
}

g5_tests() {
  coverage run -m pytest -q && coverage report
}

g6_secrets() {
  if [[ -n "$(git ls-files .env)" ]]; then
    echo "G6: .env is tracked by git"
    return 1
  fi
  mapfile -t paths < <(existing src prompts tests .harness evals pyproject.toml \
    requirements-dev.txt .gitignore .env.example)
  local scanned
  scanned="$(find "${paths[@]}" -type f -not -path '*/__pycache__/*' -not -path '*/.ruff_cache/*' | wc -l)"
  if [[ "$scanned" -lt 1 ]]; then
    echo "G6: no files scanned"
    return 1
  fi
  detect-secrets scan --all-files --exclude-files '(__pycache__|\.ruff_cache|\.pytest_cache)/' "${paths[@]}" | "$PY" -c '
import json, sys
results = json.load(sys.stdin)["results"]
for path, hits in results.items():
    for hit in hits:
        print("G6:", hit["type"], "in", path + ":" + str(hit["line_number"]))
sys.exit(1 if results else 0)
'
  local status=$?
  echo "G6: $scanned files scanned"
  return $status
}

g7_clock() {
  mapfile -t paths < <(existing src prompts)
  [[ ${#paths[@]} -eq 0 ]] && return 0
  local pattern='datetime\.now|datetime\.today|datetime\.utcnow|date\.today'
  pattern+='|time\.time|time\.monotonic|time\.localtime|time\.gmtime'
  rg -n "$pattern" "${paths[@]}"
  [[ $? -eq 1 ]]
}

g8_dataset() {
  "$PY" .harness/check_dataset.py
}

self_check() {
  "$PY" .harness/self_check.py
}

g9_evaluation() {
  if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
  "$PY" .harness/evaluate.py
}

gate "G1 Integrity" g1_integrity
gate "G2 Suppressions" g2_suppressions
gate "G3 Lint/format" g3_lint
gate "G4 Security" g4_security
gate "G5 Unit tests" g5_tests
gate "G6 Secrets" g6_secrets
gate "G7 Clock" g7_clock
gate "G8 Dataset" g8_dataset
gate "SC Harness self-check" self_check
if [[ $OFFLINE -eq 0 ]]; then
  gate "G9 Evaluation" g9_evaluation
else
  echo "SKIP G9 Evaluation (--offline)"
fi

exit $FAILED
