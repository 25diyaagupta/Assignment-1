"""Parsing the model reply into an Interpretation (data-model.md §Interpretation)."""

from __future__ import annotations

import json

import pytest

from conftest import interp
from reminder_agent.errors import InvalidModelOutput
from reminder_agent.interpretation import Interpretation, parse_interpretation


@pytest.mark.covers("INV-001", "INV-002")
def test_valid_reply_is_parsed():
    result = parse_interpretation(
        interp(decision="create", task="call the plumber", due_local="2026-03-05T09:00")
    )
    assert isinstance(result, Interpretation)
    assert result.decision == "create"
    assert result.task == "call the plumber"
    assert result.due_local == "2026-03-05T09:00"
    assert result.relative_minutes is None


@pytest.mark.covers("INV-001")
@pytest.mark.parametrize("text", ["", "not json", "[1, 2]", "Sure! {}", "null"])
def test_non_object_replies_are_rejected(text):
    with pytest.raises(InvalidModelOutput):
        parse_interpretation(text)


def mutated(**changes):
    data = json.loads(interp(decision="create", task="x", due_local="2026-03-05T09:00"))
    data.update(changes)
    return json.dumps(data)


@pytest.mark.covers("INV-002", "INV-004")
@pytest.mark.parametrize(
    "text",
    [
        mutated(decision="delete"),
        mutated(refusal_reason="because"),
        mutated(task=7),
        mutated(due_local="tomorrow 9am"),
        mutated(due_local="2026-02-30T09:00"),
        mutated(relative_minutes=30),
        mutated(due_local=None, relative_minutes=-1),
        mutated(due_local=None, relative_minutes=1.5),
        mutated(snooze_minutes=0),
        mutated(snooze_minutes=True),
        mutated(extra_field=1),
    ],
)
def test_invalid_fields_are_rejected(text):
    with pytest.raises(InvalidModelOutput):
        parse_interpretation(text)


@pytest.mark.covers("INV-004")
def test_missing_keys_are_rejected():
    data = json.loads(interp(decision="clarify", question="When?"))
    del data["refusal_reason"]
    with pytest.raises(InvalidModelOutput):
        parse_interpretation(json.dumps(data))
