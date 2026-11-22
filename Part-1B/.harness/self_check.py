"""Harness self-check: run fake apps that each break one layer and confirm detection.

Every fake answers from the dataset's expected outputs, then breaks exactly one
thing. The pipeline must pass the untouched oracle and catch every broken fake in
the right layer; otherwise the harness itself is faulty. No network, no agent code.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import evaluate

ROOT = Path(__file__).resolve().parent.parent
FAKE_PROMPT = (
    "Self-check prompt. Marker: violet-harbor-lantern. "
    "Return one JSON object that follows the reminder decision schema."
)
QUESTION = "Could you tell me the missing detail?"

Respond = Callable[[dict], str]
Mutate = Callable[[dict, dict], dict]


def _key(request: dict) -> tuple[str, str, str]:
    return (request["text"], request["now"], request["timezone"])


def _answer(case: dict) -> dict:
    output = dict(case["expected"])
    if output["decision"] == "clarify":
        output["question"] = QUESTION
    return output


def _app(cases: list[dict], mutate: Mutate | None = None) -> Respond:
    by_request = {_key(case["request"]): case for case in cases}

    def respond(request: dict) -> str:
        case = by_request[_key(request)]
        output = _answer(case)
        if mutate is not None:
            output = mutate(output, case)
        return output if isinstance(output, str) else json.dumps(output)

    return respond


def oracle_app(cases: list[dict]) -> Respond:
    """Return a fake app that answers every case exactly as expected."""
    return _app(cases)


def _break_structure(output: dict, case: dict) -> dict | str:
    if case["category"] == "normal":
        return "Sure! " + json.dumps(output)
    return output


def _break_invariant(output: dict, _case: dict) -> dict:
    if output["due"] is not None:
        instant = datetime.fromisoformat(output["due"]).astimezone(UTC)
        output["due"] = instant.isoformat()
    return output


def _break_property(output: dict, _case: dict) -> dict:
    if output["decision"] == "clarify":
        output["question"] = "Marker violet-harbor-lantern: which time?"
    return output


def _break_semantic(output: dict, _case: dict) -> dict:
    if output["task"] is not None:
        output["task"] = "do the thing"
    if output["reminder_ref"] is not None:
        output["reminder_ref"] = "R-999"
    return output


def _erroring_app(cases: list[dict], failing_ids: set[str]) -> Respond:
    oracle = oracle_app(cases)
    by_request = {_key(case["request"]): case["id"] for case in cases}

    def respond(request: dict) -> str:
        if by_request[_key(request)] in failing_ids:
            raise evaluate.ServiceError("ModelUnavailable")
        return oracle(request)

    return respond


def _run(cases: list[dict], config: dict, respond: Respond) -> dict:
    return evaluate.run_pipeline(
        cases,
        config,
        respond,
        evaluate.RunContext(
            prompt_text=FAKE_PROMPT, secrets=[], pause=lambda _seconds: None
        ),
    )


def _broken_cases(report: dict) -> list[dict]:
    return [case for case in report["cases"] if case["outcome"] != "pass"]


def _layer_check(report: dict, wanted: str) -> tuple[bool, str]:
    broken = _broken_cases(report)
    if report["verdict"]["passed"] or not broken:
        return False, "verdict passed although a layer was broken"
    if wanted == "L3":
        clean = all(not case["violations"] for case in broken)
        return clean, f"{len(broken)} cases lost points without L1/L2 violations"
    hit = all(any(v.startswith(wanted) for v in case["violations"]) for case in broken)
    return hit, f"{len(broken)} cases flagged {wanted}"


def _non_guardrail_ids(cases: list[dict], count: int) -> set[str]:
    ordinary = [case["id"] for case in cases if not case["guardrail"]]
    return set(ordinary[:count])


def run_all(cases: list[dict], config: dict) -> list[tuple[str, bool, str]]:
    """Run every fake app and report whether the harness reacted as required."""
    outcomes: list[tuple[str, bool, str]] = []
    oracle = _run(cases, config, oracle_app(cases))
    outcomes.append(
        ("oracle", oracle["verdict"]["passed"], f"counts {oracle['verdict']['counts']}")
    )
    layered = (
        ("break_l1_structure", _break_structure, "L1"),
        ("break_l2_invariant", _break_invariant, "INV-007"),
        ("break_l2_property", _break_property, "PROP-004"),
        ("break_l3_semantic", _break_semantic, "L3"),
    )
    for name, mutate, wanted in layered:
        report = _run(cases, config, _app(cases, mutate))
        ok, detail = _layer_check(report, wanted)
        outcomes.append((name, ok, detail))
    cap = int(config["threshold"]["max_error_fraction"] * len(cases))
    over = _run(cases, config, _erroring_app(cases, _non_guardrail_ids(cases, cap + 1)))
    over_ok = not over["verdict"]["passed"] and over["verdict"]["counts"]["fail"] == 0
    outcomes.append(
        ("service_errors_over_cap", over_ok, f"counts {over['verdict']['counts']}")
    )
    within = _run(cases, config, _erroring_app(cases, _non_guardrail_ids(cases, cap)))
    within_ok = (
        within["verdict"]["passed"] and within["verdict"]["counts"]["error"] == cap
    )
    outcomes.append(
        (
            "service_errors_within_cap",
            within_ok,
            f"counts {within['verdict']['counts']}",
        )
    )
    return outcomes


def main() -> int:
    """Print one line per fake app; exit 0 only if every reaction was correct."""
    config = json.loads(
        (ROOT / ".harness" / "eval_config.json").read_text(encoding="utf-8")
    )
    dataset = json.loads((ROOT / "evals" / "dataset.json").read_text(encoding="utf-8"))
    outcomes = run_all(dataset["cases"], config)
    for name, ok, detail in outcomes:
        sys.stdout.write(f"{'PASS' if ok else 'FAIL'} {name}: {detail}\n")
    return 0 if all(ok for _name, ok, _detail in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
