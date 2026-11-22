"""US3: reschedule or snooze an existing reminder (spec.md User Story 3)."""

from __future__ import annotations

import pytest

from conftest import KOLKATA, KOLKATA_NOW, interp
from reminder_agent import Request, handle_request


def decide(fake_client, reply, text="Move it"):
    client = fake_client(reply)
    request = Request(text=text, now=KOLKATA_NOW, timezone=KOLKATA)
    return handle_request(request, client).to_dict()


def assert_clarify(output):
    assert output["decision"] == "clarify"
    assert output["question"].strip()
    assert output["due"] is None
    assert output["reminder_ref"] is None


@pytest.mark.covers("FR-010", "FR-012", "INV-003")
def test_reschedule_to_friday(fake_client):
    reply = interp(
        decision="reschedule", reminder_ref="R-104", due_local="2026-03-06T11:00"
    )
    output = decide(fake_client, reply, text="Move reminder R-104 to Friday at 11am")
    assert output == {
        "decision": "reschedule",
        "task": None,
        "due": "2026-03-06T11:00:00+05:30",
        "reminder_ref": "R-104",
        "snooze_minutes": None,
        "question": None,
        "refusal_reason": None,
    }


@pytest.mark.covers("FR-010")
def test_reschedule_may_carry_restated_task(fake_client):
    reply = interp(
        decision="reschedule",
        reminder_ref="R-104",
        task="call the plumber",
        due_local="2026-03-06T11:00",
    )
    assert decide(fake_client, reply)["task"] == "call the plumber"


@pytest.mark.covers("FR-011", "INV-003")
@pytest.mark.parametrize("minutes", [15, 120])
def test_snooze(fake_client, minutes):
    reply = interp(decision="snooze", reminder_ref="R-221", snooze_minutes=minutes)
    assert decide(fake_client, reply) == {
        "decision": "snooze",
        "task": None,
        "due": None,
        "reminder_ref": "R-221",
        "snooze_minutes": minutes,
        "question": None,
        "refusal_reason": None,
    }


@pytest.mark.covers("FR-011")
def test_snooze_ignores_any_due_from_model(fake_client):
    reply = interp(
        decision="snooze",
        reminder_ref="R-221",
        snooze_minutes=15,
        due_local="2026-03-04T10:15",
    )
    assert decide(fake_client, reply)["due"] is None


@pytest.mark.covers("FR-012")
def test_snooze_without_period_becomes_clarify(fake_client):
    reply = interp(decision="snooze", reminder_ref="R-310")
    assert_clarify(decide(fake_client, reply, text="Snooze R-310"))


@pytest.mark.covers("FR-012")
def test_snooze_without_reference_becomes_clarify(fake_client):
    reply = interp(decision="snooze", snooze_minutes=10)
    assert_clarify(decide(fake_client, reply, text="Snooze it for 10 minutes"))


@pytest.mark.covers("FR-012")
def test_reschedule_without_reference_becomes_clarify(fake_client):
    reply = interp(decision="reschedule", due_local="2026-03-05T16:00")
    assert_clarify(
        decide(fake_client, reply, text="Push my reminder to Thursday at 4pm")
    )


@pytest.mark.covers("FR-012")
def test_reschedule_without_time_becomes_clarify(fake_client):
    reply = interp(decision="reschedule", reminder_ref="R-104")
    assert_clarify(decide(fake_client, reply, text="Move reminder R-104"))


@pytest.mark.covers("FR-012", "INV-006")
def test_reschedule_to_past_time_becomes_clarify(fake_client):
    reply = interp(
        decision="reschedule", reminder_ref="R-104", due_local="2026-03-04T09:00"
    )
    assert_clarify(decide(fake_client, reply, text="Move reminder R-104 to 9am today"))
