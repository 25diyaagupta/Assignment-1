"""US2: ask instead of guessing (spec.md User Story 2)."""

from __future__ import annotations

import pytest

from conftest import KOLKATA, KOLKATA_NOW, NEW_YORK, NY_DST_NOW, interp
from reminder_agent import Request, handle_request


def decide(fake_client, reply, now=KOLKATA_NOW, tz=KOLKATA, text="Remind me"):
    client = fake_client(reply)
    return handle_request(Request(text=text, now=now, timezone=tz), client).to_dict()


def assert_clarify(output):
    assert output["decision"] == "clarify"
    assert isinstance(output["question"], str)
    assert output["question"].strip()
    for key in ("task", "due", "reminder_ref", "snooze_minutes", "refusal_reason"):
        assert output[key] is None, key


@pytest.mark.covers("FR-009", "PROP-001")
def test_model_clarify_passes_question_through(fake_client):
    output = decide(
        fake_client,
        interp(decision="clarify", question="What should I remind you about?"),
    )
    assert_clarify(output)
    assert output["question"] == "What should I remind you about?"


@pytest.mark.covers("FR-009")
@pytest.mark.parametrize("question", [None, "", "   "])
def test_empty_question_is_replaced_by_default(fake_client, question):
    assert_clarify(decide(fake_client, interp(decision="clarify", question=question)))


@pytest.mark.covers("FR-009", "PROP-001")
def test_clarify_drops_any_guessed_fields(fake_client):
    reply = interp(
        decision="clarify",
        question="Which time?",
        task="feed the cat",
        due_local="2026-03-04T19:00",
    )
    assert_clarify(decide(fake_client, reply))


@pytest.mark.covers("FR-007", "PROP-001")
def test_create_without_task_becomes_clarify(fake_client):
    reply = interp(decision="create", task=None, due_local="2026-03-05T09:00")
    assert_clarify(decide(fake_client, reply, text="Remind me tomorrow at 9am"))


@pytest.mark.covers("FR-007", "PROP-001")
def test_create_without_time_becomes_clarify(fake_client):
    reply = interp(decision="create", task="book the vet")
    assert_clarify(decide(fake_client, reply, text="Remind me to book the vet"))


@pytest.mark.covers("FR-008", "INV-006", "PROP-001")
def test_time_already_passed_today_becomes_clarify(fake_client):
    reply = interp(
        decision="create", task="lock the shed", due_local="2026-03-04T17:00"
    )
    output = decide(fake_client, reply, now="2026-03-04T18:00:00+05:30")
    assert_clarify(output)


@pytest.mark.covers("INV-006")
def test_negative_duration_is_not_accepted(fake_client):
    reply = interp(decision="create", task="lock the shed", relative_minutes=-5)
    with pytest.raises(Exception) as caught:
        decide(fake_client, reply)
    assert type(caught.value).__name__ == "InvalidModelOutput"


@pytest.mark.covers("FR-008", "PROP-001")
def test_nonexistent_dst_time_becomes_clarify(fake_client):
    reply = interp(
        decision="create", task="check the boiler", due_local="2026-03-08T02:30"
    )
    assert_clarify(decide(fake_client, reply, now=NY_DST_NOW, tz=NEW_YORK))


@pytest.mark.covers("FR-008", "PROP-001")
def test_ambiguous_fall_back_time_becomes_clarify(fake_client):
    reply = interp(
        decision="create", task="check the boiler", due_local="2026-11-01T01:30"
    )
    output = decide(fake_client, reply, now="2026-10-31T12:00:00-04:00", tz=NEW_YORK)
    assert_clarify(output)
