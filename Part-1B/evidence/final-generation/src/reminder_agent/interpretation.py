"""Parse and validate the model reply (data-model.md §Interpretation; research R4)."""

import json
import re
from dataclasses import dataclass
from datetime import datetime

from reminder_agent.errors import InvalidModelOutput

DECISIONS = ("create", "reschedule", "snooze", "clarify", "refuse")
REFUSAL_REASONS = ("prompt_extraction", "instruction_override", "out_of_scope")
KEYS = (
    "decision",
    "task",
    "due_local",
    "relative_minutes",
    "reminder_ref",
    "snooze_minutes",
    "question",
    "refusal_reason",
)
TEXT_FIELDS = ("task", "reminder_ref", "question")
DUE_LOCAL = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


@dataclass(frozen=True)
class Interpretation:
    """What the model understood; never contains an offset or computed instant."""

    decision: str
    task: str | None
    due_local: str | None
    relative_minutes: int | None
    reminder_ref: str | None
    snooze_minutes: int | None
    question: str | None
    refusal_reason: str | None


def _load_object(text: str) -> dict[str, object]:
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise InvalidModelOutput("reply is not JSON") from exc
    if not isinstance(data, dict):
        raise InvalidModelOutput("reply is not a JSON object")
    if set(data) != set(KEYS):
        raise InvalidModelOutput("reply keys do not match the interpretation")
    return data


def _check_int(data: dict[str, object], key: str, minimum: int) -> None:
    value = data[key]
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InvalidModelOutput(f"{key} must be a whole number >= {minimum}")


def _check_due_local(value: object) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not DUE_LOCAL.match(value):
        raise InvalidModelOutput("due_local must look like YYYY-MM-DDTHH:MM")
    try:
        datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidModelOutput("due_local is not a real date and time") from exc


def _check_enums(data: dict[str, object]) -> None:
    if data["decision"] not in DECISIONS:
        raise InvalidModelOutput("decision is outside the enumeration")
    reason = data["refusal_reason"]
    if reason is not None and reason not in REFUSAL_REASONS:
        raise InvalidModelOutput("refusal_reason is outside the enumeration")
    if data["decision"] == "refuse" and reason is None:
        raise InvalidModelOutput("refuse needs a refusal_reason")


def parse_interpretation(text: str) -> Interpretation:
    """Return the Interpretation in ``text`` or raise ``InvalidModelOutput``."""
    data = _load_object(text)
    _check_enums(data)
    for key in TEXT_FIELDS:
        if data[key] is not None and not isinstance(data[key], str):
            raise InvalidModelOutput(f"{key} must be a string or null")
    _check_due_local(data["due_local"])
    _check_int(data, "relative_minutes", 0)
    _check_int(data, "snooze_minutes", 1)
    if data["due_local"] is not None and data["relative_minutes"] is not None:
        raise InvalidModelOutput("due_local and relative_minutes are exclusive")
    return Interpretation(**data)  # type-checked field by field above
