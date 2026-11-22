"""FR-001/FR-003: request validation before any model call."""

from __future__ import annotations

import pytest

from conftest import KOLKATA, KOLKATA_NOW, interp
from reminder_agent import Request, handle_request
from reminder_agent.errors import InvalidRequest


@pytest.mark.covers("FR-003")
@pytest.mark.parametrize(
    ("now", "tz"),
    [
        ("2026-03-04T10:00:00", KOLKATA),
        ("not a date", KOLKATA),
        ("", KOLKATA),
        (KOLKATA_NOW, "Mars/Olympus_Mons"),
        (KOLKATA_NOW, ""),
    ],
)
def test_bad_context_is_rejected(now, tz):
    with pytest.raises(InvalidRequest):
        Request(
            text="Remind me to call the plumber tomorrow at 9am", now=now, timezone=tz
        )


@pytest.mark.covers("FR-003")
def test_rejected_request_makes_no_model_call(fake_client):
    client = fake_client(interp(decision="clarify", question="?"))
    with pytest.raises(InvalidRequest):
        handle_request(Request(text="x", now="yesterday", timezone=KOLKATA), client)
    assert client.calls == []


@pytest.mark.covers("FR-001", "FR-007")
def test_empty_text_is_accepted_and_interpreted(fake_client):
    client = fake_client(
        interp(decision="clarify", question="What should I remind you about?")
    )
    output = handle_request(Request(text="", now=KOLKATA_NOW, timezone=KOLKATA), client)
    assert output.to_dict()["decision"] == "clarify"
    assert len(client.calls) == 1
