"""US1: create a reminder from a sentence (spec.md User Story 1)."""

from __future__ import annotations

import json

import pytest

from conftest import KOLKATA, KOLKATA_NOW, NEW_YORK, NY_DST_NOW, interp
from reminder_agent import DecisionOutput, Request, handle_request

OUTPUT_KEYS = {
    "decision",
    "task",
    "due",
    "reminder_ref",
    "snooze_minutes",
    "question",
    "refusal_reason",
}


def create_output(fake_client, reply, text="Remind me", now=KOLKATA_NOW, tz=KOLKATA):
    client = fake_client(reply)
    result = handle_request(Request(text=text, now=now, timezone=tz), client)
    return result, client


@pytest.mark.covers("FR-001", "FR-002", "FR-004", "FR-005", "INV-003", "INV-004")
def test_plumber_tomorrow_at_nine(fake_client):
    reply = interp(
        decision="create", task="call the plumber", due_local="2026-03-05T09:00"
    )
    result, _ = create_output(
        fake_client, reply, text="Remind me to call the plumber tomorrow at 9am"
    )
    assert isinstance(result, DecisionOutput)
    assert result.to_dict() == {
        "decision": "create",
        "task": "call the plumber",
        "due": "2026-03-05T09:00:00+05:30",
        "reminder_ref": None,
        "snooze_minutes": None,
        "question": None,
        "refusal_reason": None,
    }


@pytest.mark.covers("FR-002", "INV-001", "INV-004")
def test_to_json_is_one_object_with_seven_keys(fake_client):
    reply = interp(
        decision="create", task="call the plumber", due_local="2026-03-05T09:00"
    )
    result, _ = create_output(fake_client, reply)
    text = result.to_json()
    parsed = json.loads(text)
    assert set(parsed) == OUTPUT_KEYS
    assert text.strip().startswith("{")
    assert text.strip().endswith("}")


@pytest.mark.covers("FR-006", "PROP-002", "INV-005")
@pytest.mark.parametrize(
    ("reply", "now", "tz", "due"),
    [
        (
            interp(decision="create", task="take the bread out", relative_minutes=45),
            KOLKATA_NOW,
            KOLKATA,
            "2026-03-04T10:45:00+05:30",
        ),
        (
            interp(
                decision="create", task="water the ferns", due_local="2026-03-08T10:00"
            ),
            NY_DST_NOW,
            NEW_YORK,
            "2026-03-08T10:00:00-04:00",
        ),
        (
            interp(
                decision="create", task="renew the permit", due_local="2027-01-01T08:00"
            ),
            "2026-12-31T23:30:00-05:00",
            NEW_YORK,
            "2027-01-01T08:00:00-05:00",
        ),
        (
            interp(
                decision="create", task="switch off the heater", relative_minutes=90
            ),
            "2026-03-04T23:00:00+05:30",
            KOLKATA,
            "2026-03-05T00:30:00+05:30",
        ),
        (
            interp(
                decision="create", task="lock the shed", due_local="2026-03-04T17:00"
            ),
            KOLKATA_NOW,
            KOLKATA,
            "2026-03-04T17:00:00+05:30",
        ),
    ],
)
def test_due_resolution(fake_client, reply, now, tz, due):
    result, _ = create_output(fake_client, reply, now=now, tz=tz)
    assert result.to_dict()["decision"] == "create"
    assert result.to_dict()["due"] == due


@pytest.mark.covers("INV-007", "PROP-002")
def test_duration_across_dst_uses_offset_at_due_instant(fake_client):
    reply = interp(decision="create", task="check the oven", relative_minutes=24 * 60)
    result, _ = create_output(fake_client, reply, now=NY_DST_NOW, tz=NEW_YORK)
    assert result.to_dict()["due"] == "2026-03-08T13:00:00-04:00"


@pytest.mark.covers("INV-006")
def test_due_equal_to_now_is_allowed(fake_client):
    reply = interp(decision="create", task="stand up", relative_minutes=0)
    result, _ = create_output(fake_client, reply)
    assert result.to_dict()["decision"] == "create"
    assert result.to_dict()["due"] == "2026-03-04T10:00:00+05:30"


@pytest.mark.covers("FR-001", "FR-006")
def test_one_model_call_with_request_and_calendar_facts(fake_client):
    reply = interp(
        decision="create", task="call the plumber", due_local="2026-03-05T09:00"
    )
    text = "Remind me to call the plumber tomorrow at 9am"
    _, client = create_output(fake_client, reply, text=text)
    assert len(client.calls) == 1
    system, user, schema = client.calls[0]
    assert system.strip()
    assert text in user
    assert KOLKATA_NOW in user
    assert KOLKATA in user
    for day in range(5, 19):
        assert f"2026-03-{day:02d}" in user
    assert "Wednesday" in user
    assert isinstance(schema, dict)
    assert schema


@pytest.mark.covers("FR-005")
def test_task_is_kept_as_given_by_model(fake_client):
    reply = interp(
        decision="create", task="submit the Zorvan report", due_local="2026-03-09T15:00"
    )
    result, _ = create_output(fake_client, reply)
    assert result.to_dict()["task"] == "submit the Zorvan report"
