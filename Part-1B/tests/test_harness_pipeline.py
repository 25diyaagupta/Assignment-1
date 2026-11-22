"""US5: the L1 -> L2 -> L3 pipeline and the fake-app self-check (FR-019..FR-024)."""

from __future__ import annotations

import json
from pathlib import Path

import evaluate
import pytest
import self_check

ROOT = Path(__file__).resolve().parent.parent
DATASET = json.loads((ROOT / "evals" / "dataset.json").read_text())
CONFIG = json.loads((ROOT / ".harness" / "eval_config.json").read_text())
PROMPT = (
    "Synthetic prompt for tests. Marker: violet-harbor-lantern. Answer with JSON only."
)


def run(respond, cases=None):
    return evaluate.run_pipeline(
        cases or DATASET["cases"],
        CONFIG,
        respond,
        evaluate.RunContext(
            prompt_text=PROMPT, secrets=[], pause=lambda _seconds: None
        ),
    )


@pytest.mark.covers("FR-019", "FR-021", "FR-023", "FR-024")
def test_oracle_app_passes_every_case():
    report = run(self_check.oracle_app(DATASET["cases"]))
    assert report["verdict"]["passed"] is True
    assert report["verdict"]["counts"] == {"pass": 30, "fail": 0, "error": 0}
    assert report["verdict"]["overall_mean"] == 1.0


@pytest.mark.covers("FR-019", "INV-001")
def test_each_case_is_run_three_times():
    calls = []
    oracle = self_check.oracle_app(DATASET["cases"])

    def counting(request):
        calls.append(request["text"])
        return oracle(request)

    run(counting, DATASET["cases"][:2])
    assert len(calls) == 6


@pytest.mark.covers("FR-019", "INV-001", "INV-004")
def test_l1_failure_skips_l2_and_l3():
    case = DATASET["cases"][0]
    report = run(lambda _request: '{"decision": "create", "extra": 1}', [case])
    result = report["cases"][0]
    assert result["outcome"] == "fail"
    assert all(rep["l1_pass"] is False for rep in result["reps"])
    assert all(rep["components"] == {} for rep in result["reps"])


@pytest.mark.covers("FR-022")
def test_service_errors_are_retried_then_recorded_as_error():
    attempts = []

    def flaky(_request):
        attempts.append(1)
        raise evaluate.ServiceError("ModelUnavailable")

    report = run(flaky, DATASET["cases"][:1])
    retries = CONFIG["pacing"]["service_error_retries"]
    assert len(attempts) == 3 * (1 + retries)
    assert report["cases"][0]["outcome"] == "error"
    assert report["verdict"]["counts"]["fail"] == 0


@pytest.mark.covers("FR-022")
def test_agent_crash_is_a_wrong_answer_not_an_error():
    def crashing(_request):
        raise ValueError("unusable model output")

    report = run(crashing, DATASET["cases"][:1])
    assert report["cases"][0]["outcome"] == "fail"
    assert report["verdict"]["counts"]["error"] == 0


@pytest.mark.covers("FR-022")
def test_config_error_aborts_run():
    def misconfigured(_request):
        raise evaluate.ConfigError("ModelConfigError")

    with pytest.raises(evaluate.ConfigError):
        run(misconfigured, DATASET["cases"][:1])


@pytest.mark.covers("FR-019", "FR-020", "FR-021", "FR-022", "FR-023", "FR-024")
def test_self_check_detects_every_broken_layer():
    outcomes = self_check.run_all(DATASET["cases"], CONFIG)
    assert {name for name, _ok, _detail in outcomes} >= {
        "oracle",
        "break_l1_structure",
        "break_l2_invariant",
        "break_l2_property",
        "break_l3_semantic",
        "service_errors_over_cap",
        "service_errors_within_cap",
    }
    failed = [(name, detail) for name, ok, detail in outcomes if not ok]
    assert failed == []


@pytest.mark.covers("FR-023")
def test_report_is_written_without_secrets(tmp_path):
    report = run(self_check.oracle_app(DATASET["cases"]), DATASET["cases"][:2])
    paths = evaluate.write_report(report, tmp_path, label="unit")
    text = "".join(path.read_text() for path in paths)
    assert "pass" in text
    assert "x-goog-api-key" not in text
