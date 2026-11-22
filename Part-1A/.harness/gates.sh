#!/usr/bin/env bash
# Gate library for the lean-scope harness (constitution v1.0.2, plan.md §Harness Gates).
#
# Each gate_gN takes a root directory, runs its check inside that directory, prints
# "PASS GN" or "FAIL GN", and returns non-zero on failure. Sourced by run.sh and
# self_check.sh. A gate that cannot run its check (missing tool, missing directory,
# nothing to scan) fails: an absent result is never a pass.

_HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_REPO_ROOT="$(cd "$_HARNESS_DIR/.." && pwd)"

# Prefer the tools pinned in the repository's .venv; fall back to PATH.
_tool() {
    if [ -x "$_REPO_ROOT/.venv/bin/$1" ]; then
        echo "$_REPO_ROOT/.venv/bin/$1"
    else
        command -v "$1" || echo "$1"
    fi
}

_report() {  # _report <gate> <status>
    if [ "$2" -eq 0 ]; then echo "PASS $1"; else echo "FAIL $1"; fi
    return "$2"
}

# G1 Integrity: tests/ and .harness/ unchanged since tag harness-approved.
# Compares the tag with the working tree (committed and uncommitted edits) and
# lists untracked files, so a change cannot hide outside a commit.
gate_g1() {
    local rc=0
    (
        cd "$1" || exit 2
        if ! git rev-parse -q --verify refs/tags/harness-approved >/dev/null; then
            echo "WARN G1: tag harness-approved does not exist yet; integrity not checked"
            exit 0
        fi
        changed="$(git diff --name-only harness-approved -- tests .harness)" || exit 2
        untracked="$(git ls-files --others --exclude-standard -- tests .harness)" || exit 2
        if [ -n "$changed$untracked" ]; then
            printf 'G1: changed since harness-approved:\n%s\n%s\n' "$changed" "$untracked"
            exit 1
        fi
    ) || rc=$?
    _report G1 "$rc"
}

# G2 Suppressions: suppression comment syntax in *.py files only.
gate_g2() {
    local rc=0
    if ! command -v rg >/dev/null 2>&1; then
        echo "G2: rg (ripgrep) not found on PATH"
        _report G2 2
        return
    fi
    (
        cd "$1" || exit 2
        rg -n --hidden --glob '*.py' --glob '!.venv/**' \
            -e '#\s*(noqa|nosec|type:\s*ignore|pragma:\s*no\s*cover|fmt:\s*off)' .
        case $? in
            0) exit 1 ;;   # matches found
            1) exit 0 ;;   # no matches
            *) exit 2 ;;   # rg error
        esac
    ) || rc=$?
    _report G2 "$rc"
}

# G3 Lint/format: full rule set on src/, tests/ruff.toml set on tests/.
gate_g3() {
    local rc=0 ruff
    ruff="$(_tool ruff)"
    (
        cd "$1" || exit 2
        for d in src tests; do
            [ -d "$d" ] || { echo "G3: $d/ not found"; exit 2; }
        done
        "$ruff" check src tests || exit 1
        "$ruff" format --check src tests || exit 1
    ) || rc=$?
    _report G3 "$rc"
}

# G4 Security: bandit over src/ at every severity and confidence level.
gate_g4() {
    local rc=0 bandit
    bandit="$(_tool bandit)"
    (
        cd "$1" || exit 2
        [ -d src ] || { echo "G4: src/ not found"; exit 2; }
        "$bandit" -q -r src || exit 1
    ) || rc=$?
    _report G4 "$rc"
}

# G5 Tests and coverage: all tests pass and branch coverage >= 90 %.
# The threshold is passed on the command line, so a config file cannot lower it.
gate_g5() {
    local rc=0 coverage start end
    coverage="$(_tool coverage)"
    start="$EPOCHREALTIME"
    (
        cd "$1" || exit 2
        "$coverage" erase || exit 2
        "$coverage" run --branch -m pytest -q -p no:cacheprovider || exit 1
        "$coverage" report --fail-under=90 || exit 1
    ) || rc=$?
    end="$EPOCHREALTIME"
    echo "G5: wall time $(awk -v a="$start" -v b="$end" 'BEGIN { printf "%.2f", b - a }') s"
    _report G5 "$rc"
}

# G6 Secrets: detect-secrets over the project files only (constitution VII, v1.0.3):
# src/, tests/, .harness/ and the root config files, tracked and untracked (not ignored).
# Every detector is enabled. Zero files scanned is a failure.
G6_SCOPE=(src tests .harness pyproject.toml requirements-dev.txt .gitignore)
gate_g6() {
    local rc=0 ds py
    ds="$(_tool detect-secrets)"
    py="$(_tool python)"
    (
        cd "$1" || exit 2
        if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
            mapfile -t files < <(git ls-files --cached --others --exclude-standard -- "${G6_SCOPE[@]}")
        else
            mapfile -t files < <(find "${G6_SCOPE[@]}" -type f 2>/dev/null)
        fi
        [ "${#files[@]}" -gt 0 ] || { echo "G6: zero files to scan"; exit 2; }
        echo "G6: scanning ${#files[@]} files"
        "$ds" scan "${files[@]}" | "$py" -c '
import json, sys
results = json.load(sys.stdin)["results"]
for path, found in results.items():
    for item in found:
        print("G6:", path, "line", item["line_number"], item["type"])
sys.exit(1 if results else 0)
' || exit 1
    ) || rc=$?
    _report G6 "$rc"
}
