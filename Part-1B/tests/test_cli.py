"""CLI contract (contracts/agent-api.md §CLI)."""

from __future__ import annotations

import io
import json

import pytest

from conftest import KOLKATA, KOLKATA_NOW, FakeModelClient, interp
from reminder_agent.__main__ import main
from reminder_agent.errors import InvalidModelOutput, ModelConfigError, ModelTimeout

PLACEHOLDER = "-".join(["cli", "placeholder", "credential"])
ENVIRON = {"GEMINI_API_KEY": PLACEHOLDER}
REQUEST = {
    "text": "Remind me to call the plumber tomorrow at 9am",
    "now": KOLKATA_NOW,
    "timezone": KOLKATA,
}


def run(stdin_text, *script, factory=None):
    client = FakeModelClient(script)
    stdout, stderr = io.StringIO(), io.StringIO()
    code = main(
        io.StringIO(stdin_text),
        stdout,
        stderr,
        ENVIRON,
        factory or (lambda _environ: client),
    )
    return code, stdout.getvalue(), stderr.getvalue(), client


@pytest.mark.covers("FR-001", "FR-002")
def test_success_writes_one_decision():
    reply = interp(
        decision="create", task="call the plumber", due_local="2026-03-05T09:00"
    )
    code, out, err, _ = run(json.dumps(REQUEST), reply)
    assert code == 0
    assert err == ""
    assert json.loads(out)["due"] == "2026-03-05T09:00:00+05:30"


@pytest.mark.covers("FR-003")
@pytest.mark.parametrize(
    "stdin_text",
    [
        "not json",
        json.dumps({"text": "x", "now": KOLKATA_NOW}),
        json.dumps({**REQUEST, "now": "2026-03-04T10:00:00"}),
        json.dumps({**REQUEST, "timezone": "Nowhere/Place"}),
    ],
)
def test_invalid_request_exits_2_without_model_call(stdin_text):
    code, out, err, client = run(stdin_text)
    assert code == 2
    assert out == ""
    assert err.strip()
    assert client.calls == []


@pytest.mark.covers("FR-003")
def test_config_error_exits_2():
    def factory(_environ):
        raise ModelConfigError("missing key")

    code, _, err, _ = run(json.dumps(REQUEST), factory=factory)
    assert code == 2
    assert "ModelConfigError" in err


@pytest.mark.covers("FR-022")
def test_service_error_exits_3():
    code, out, err, _ = run(json.dumps(REQUEST), ModelTimeout("timed out"))
    assert code == 3
    assert out == ""
    assert "ModelTimeout" in err
    assert PLACEHOLDER not in err


@pytest.mark.covers("INV-001")
def test_invalid_model_output_exits_4():
    code, out, err, _ = run(json.dumps(REQUEST), "this is not json")
    assert code == 4
    assert out == ""
    assert InvalidModelOutput.__name__ in err


@pytest.mark.covers("PROP-004")
def test_key_is_passed_to_leak_guard():
    reply = interp(
        decision="create", task=f"read {PLACEHOLDER}", due_local="2026-03-05T09:00"
    )
    code, out, _, _ = run(json.dumps(REQUEST), reply)
    assert code == 0
    output = json.loads(out)
    assert output["decision"] == "refuse"
    assert output["refusal_reason"] == "prompt_extraction"
    assert PLACEHOLDER not in out
