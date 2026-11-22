#!/usr/bin/env bash
# G7 Self-check (constitution v1.0.2, plan.md §Harness Gates).
#
# For each gate G1-G6 this builds a small clean fake project in a fresh temporary
# directory and checks the gate in both directions:
#   1. the gate PASSES on the clean fake (so a gate that always fails, for example
#      because its tool is missing, is caught), and
#   2. the gate FAILS after one deliberate defect is added (so a gate that always
#      passes is caught).
# Nothing is written inside the repository. Exit 0 only if every check behaves.

set -u
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=gates.sh
source "$HARNESS_DIR/gates.sh"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
FAILURES=0

_git() { git -c user.name=self-check -c user.email=self-check@example.invalid "$@"; }

# A clean project: one covered module, one passing test, committed and tagged.
make_clean() {
    local d="$1"
    mkdir -p "$d/src/fakepkg" "$d/tests"
    cat >"$d/pyproject.toml" <<'EOF'
[tool.pytest.ini_options]
pythonpath = ["src"]

[tool.coverage.run]
branch = true
source = ["src"]
EOF
    cat >"$d/src/fakepkg/__init__.py" <<'EOF'
"""Clean fake package for the harness self-check."""


def double(value: int) -> int:
    """Return twice the value."""
    return value * 2
EOF
    cat >"$d/tests/test_ok.py" <<'EOF'
from fakepkg import double


def test_double():
    assert double(2) == 4
EOF
    (
        cd "$d" || exit 2
        _git init -q . && _git add -A && _git commit -q -m clean \
            && _git tag harness-approved
    ) >/dev/null
}

# Defects, one per gate. Each takes the fake project directory.
break_g1() { echo "# edited after approval" >>"$1/tests/test_ok.py"; (cd "$1" && _git commit -q -am edit); }
break_g2() { printf 'UNUSED = 1  # %s\n' "noqa" >>"$1/src/fakepkg/__init__.py"; }
break_g3() { printf '"""Module."""\n\nimport os\n' >"$1/src/fakepkg/lint.py"; }
# The eval below is deliberate: it is written into a throwaway fake for bandit to flag
# and is never executed.
break_g4() { printf '"""Module."""\n\n\ndef run(text):\n    """Run."""\n    return eval(text)\n' >"$1/src/fakepkg/danger.py"; }
break_g5_failing_test() { printf 'def test_fails():\n    assert 1 == 2\n' >"$1/tests/test_fail.py"; }
break_g5_low_coverage() {
    {
        printf '"""Uncovered."""\n\n\ndef grade(n: int) -> str:\n    """Grade."""\n'
        for i in 1 2 3 4 5 6 7 8 9; do printf '    if n == %d:\n        return "g%d"\n' "$i" "$i"; done
        printf '    return "none"\n'
    } >"$1/src/fakepkg/uncovered.py"
}
break_g6() {
    # Built by concatenation so this script itself never contains the key.
    local fake_value="AKIA""Q7X2M9K4R8T1V6W3"
    printf 'aws_access_key_id = %s\n' "$fake_value" >"$1/notes.txt"
}

# check <gate function> <defect function> <label>
check() {
    local gate="$1" defect="$2" label="$3" dir log
    dir="$(mktemp -d "$WORK/${label}.XXXX")"
    log="$dir.log"
    make_clean "$dir"
    if ! "$gate" "$dir" >"$log" 2>&1; then
        echo "SELF-CHECK BROKEN $label: gate failed on the clean fake"
        sed 's/^/    /' "$log"
        FAILURES=$((FAILURES + 1))
        return
    fi
    "$defect" "$dir" >>"$log" 2>&1
    if "$gate" "$dir" >>"$log" 2>&1; then
        echo "SELF-CHECK BROKEN $label: gate passed on the broken fake"
        sed 's/^/    /' "$log"
        FAILURES=$((FAILURES + 1))
        return
    fi
    echo "ok   $label: passes clean, fails on its defect"
}

check gate_g1 break_g1 g1-integrity
check gate_g2 break_g2 g2-suppression
check gate_g3 break_g3 g3-lint
check gate_g4 break_g4 g4-bandit
check gate_g5 break_g5_failing_test g5-failing-test
check gate_g5 break_g5_low_coverage g5-low-coverage
check gate_g6 break_g6 g6-secret

if [ "$FAILURES" -ne 0 ]; then
    echo "FAIL G7: $FAILURES self-check(s) broken"
    exit 1
fi
echo "PASS G7"
