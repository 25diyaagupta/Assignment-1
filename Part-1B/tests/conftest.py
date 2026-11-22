"""Shared fixtures: network block, fake model client, harness import path."""

from __future__ import annotations

import json
import socket
import sys
from collections.abc import Iterable
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HARNESS = ROOT / ".harness"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))

INTERPRETATION_KEYS = (
    "decision",
    "task",
    "due_local",
    "relative_minutes",
    "reminder_ref",
    "snooze_minutes",
    "question",
    "refusal_reason",
)

KOLKATA_NOW = "2026-03-04T10:00:00+05:30"
KOLKATA = "Asia/Kolkata"
NY_DST_NOW = "2026-03-07T12:00:00-05:00"
NEW_YORK = "America/New_York"
MARKER = "violet-harbor-lantern"


class NetworkBlockedError(RuntimeError):
    """Raised when a test tries to open a socket (research R9)."""


def _blocked(*_args, **_kwargs):
    raise NetworkBlockedError("network access is disabled in tests")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


class FakeModelClient:
    """Scripted ModelClient (contracts/model-client.md §FakeModelClient)."""

    def __init__(self, script: Iterable[object]):
        self._script = list(script)
        self.calls: list[tuple[str, str, object]] = []

    def generate(self, system, user, response_schema):
        self.calls.append((system, user, response_schema))
        if not self._script:
            raise AssertionError("FakeModelClient script exhausted")
        item = self._script.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


def interp(**fields) -> str:
    """Build a model reply in the data-model.md Interpretation shape."""
    unknown = set(fields) - set(INTERPRETATION_KEYS)
    if unknown:
        raise AssertionError(f"unknown interpretation keys: {sorted(unknown)}")
    return json.dumps({key: fields.get(key) for key in INTERPRETATION_KEYS})


@pytest.fixture
def fake_client():
    """Factory fixture: ``fake_client(reply, ...)`` returns a FakeModelClient."""
    return lambda *script: FakeModelClient(script)
