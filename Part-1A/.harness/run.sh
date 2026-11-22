#!/usr/bin/env bash
# Harness entry point (constitution v1.0.2): runs G1-G6 on the repository, then the
# G7 self-check. Exits 0 only if every gate passes; stops at the first failure.

set -u
HARNESS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HARNESS_DIR/.." && pwd)"
# shellcheck source=gates.sh
source "$HARNESS_DIR/gates.sh"

for gate in gate_g1 gate_g2 gate_g3 gate_g4 gate_g5 gate_g6; do
    if ! "$gate" "$ROOT"; then
        echo "HARNESS FAILED at ${gate#gate_}"
        exit 1
    fi
done

if ! bash "$HARNESS_DIR/self_check.sh"; then
    echo "HARNESS FAILED at g7"
    exit 1
fi

echo "ALL GATES PASSED"
