"""Evaluation pipeline (gate G9): L1 structure -> L2 invariants/properties -> L3 score.

``run_pipeline`` takes any ``respond(request) -> str`` callable, so the same pipeline
grades the real agent (``main``) and the fake apps of ``self_check.py``. A respond
callable signals a service error by raising ``ServiceError`` and a configuration
problem by raising ``ConfigError``; any other exception is a wrong answer.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import jsonschema
import scoring
from scoring import CaseResult, RepetitionResult

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
SCHEMA = json.loads((HARNESS / "output.schema.json").read_text(encoding="utf-8"))
VALIDATOR = jsonschema.Draft202012Validator(SCHEMA)

Respond = Callable[[dict], str]
Pause = Callable[[float], None]


class ServiceError(Exception):
    """A model or service failure: recorded as ``error``, never as a wrong answer."""


class ConfigError(Exception):
    """A configuration failure (missing key, rejected request): aborts the run."""


def layer1(raw: str) -> dict | None:
    """Return the parsed output if it is one JSON object valid under the schema."""
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(parsed, dict) or not VALIDATOR.is_valid(parsed):
        return None
    return parsed


def _call(respond: Respond, request: dict, pacing: dict, pause: Pause) -> str:
    retries = int(pacing["service_error_retries"])
    for attempt in range(retries + 1):
        try:
            return respond(dict(request))
        except ServiceError:
            if attempt == retries:
                raise
            pause(float(pacing["retry_pause_seconds"]))
    raise ServiceError("retries exhausted")


def run_repetition(
    case: dict, rep: int, respond: Respond, config: dict, context: dict
) -> RepetitionResult:
    """Run one repetition of one case through L1, L2 and L3."""
    pause: Pause = context["pause"]
    try:
        raw = _call(respond, case["request"], config["pacing"], pause)
    except ServiceError as exc:
        return RepetitionResult(rep=rep, outcome="error", error=str(exc))
    except ConfigError:
        raise
    except Exception as exc:  # the agent failed to answer: a wrong answer (FR-022)
        return RepetitionResult(rep=rep, outcome="ok", error=type(exc).__name__)
    finally:
        pause(float(config["pacing"]["request_interval_seconds"]))
    output = layer1(raw)
    if output is None:
        return RepetitionResult(rep=rep, outcome="ok", raw=raw)
    components = scoring.component_scores(output, case)
    return RepetitionResult(
        rep=rep,
        outcome="ok",
        raw=raw,
        l1_pass=True,
        violations=scoring.l2_violations(output, raw, case, context),
        components=components,
        score=scoring.repetition_score(components, config["weights"]),
        decision=output["decision"],
    )


@dataclass(frozen=True)
class RunContext:
    """Leak references and pacing for one pipeline run."""

    prompt_text: str
    secrets: list[str]
    pause: Pause = time.sleep


def run_pipeline(
    cases: list[dict], config: dict, respond: Respond, run: RunContext
) -> dict:
    """Run every case ``config['repetitions']`` times and return the full report."""
    context = {
        "prompt_text": run.prompt_text,
        "secrets": [s for s in run.secrets if s],
        "leak": config["leak"],
        "pause": run.pause,
    }
    results: list[CaseResult] = []
    for case in cases:
        reps = [
            run_repetition(case, rep, respond, config, context)
            for rep in range(1, int(config["repetitions"]) + 1)
        ]
        results.append(scoring.case_result(case, reps, config))
    return {
        "cases": [asdict(result) for result in results],
        "verdict": scoring.verdict(results, config),
    }


def _markdown(report: dict, label: str) -> str:
    verdict = report["verdict"]
    lines = [
        f"# Evaluation report {label}",
        "",
        f"Verdict: {'PASS' if verdict['passed'] else 'FAIL'}",
        f"Overall mean: {verdict['overall_mean']}",
        f"Counts: {verdict['counts']}",
        "",
        "| Condition | Holds |",
        "|---|---|",
        *[f"| {name} | {held} |" for name, held in verdict["conditions"].items()],
        "",
        "| Case | Guardrail | Outcome | Score | Violations |",
        "|---|---|---|---|---|",
    ]
    for case in report["cases"]:
        violations = ", ".join(case["violations"]) or "-"
        lines.append(
            f"| {case['case_id']} | {case['guardrail']} | {case['outcome']} "
            f"| {case['score']} | {violations} |"
        )
    return "\n".join(lines) + "\n"


def write_report(report: dict, directory: Path, label: str) -> list[Path]:
    """Write the report as JSON and Markdown; never includes keys or headers."""
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"eval-{label}.json"
    md_path = directory / f"eval-{label}.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(report, label), encoding="utf-8")
    return [json_path, md_path]


def _live_respond(secrets: list[str]) -> Respond:
    agent = importlib.import_module("reminder_agent")
    errors = importlib.import_module("reminder_agent.errors")
    client_module = importlib.import_module("reminder_agent.model_client")
    service = (errors.ModelTimeout, errors.ModelRateLimited, errors.ModelUnavailable)
    try:
        client = client_module.GeminiClient.from_env(os.environ)
    except errors.ModelConfigError as exc:
        raise ConfigError(type(exc).__name__) from exc

    def respond(request: dict) -> str:
        try:
            decision = agent.handle_request(
                agent.Request(**request), client, secrets=secrets
            )
        except service as exc:
            raise ServiceError(type(exc).__name__) from exc
        except errors.ModelConfigError as exc:
            raise ConfigError(type(exc).__name__) from exc
        return decision.to_json()

    return respond


def main() -> int:
    """Run G9 against the real agent and Gemini; exit 0 only on a passing verdict."""
    config = json.loads((HARNESS / "eval_config.json").read_text(encoding="utf-8"))
    dataset = json.loads((ROOT / "evals" / "dataset.json").read_text(encoding="utf-8"))
    prompt_path = ROOT / "prompts" / "system.md"
    prompt_text = (
        prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
    )
    if config["leak"]["marker"] not in prompt_text:
        sys.stderr.write("G9: leak marker missing from prompts/system.md\n")
        return 1
    secrets = [os.environ.get("GEMINI_API_KEY", "")]
    try:
        respond = _live_respond(secrets)
        run = RunContext(prompt_text=prompt_text, secrets=secrets)
        report = run_pipeline(dataset["cases"], config, respond, run)
    except ConfigError as exc:
        sys.stderr.write(f"G9 aborted: {exc}\n")
        return 2
    label = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    for path in write_report(report, ROOT / "reports", label):
        sys.stdout.write(f"report: {path.relative_to(ROOT)}\n")
    sys.stdout.write(json.dumps(report["verdict"], indent=2) + "\n")
    return 0 if report["verdict"]["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
