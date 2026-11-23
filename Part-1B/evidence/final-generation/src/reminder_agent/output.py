"""The public seven-key decision (spec.md §Output Schema; FR-002, INV-002..INV-004)."""

import json
from dataclasses import asdict, dataclass

from reminder_agent.interpretation import DECISIONS, REFUSAL_REASONS

OUTPUT_KEYS = (
    "decision",
    "task",
    "due",
    "reminder_ref",
    "snooze_minutes",
    "question",
    "refusal_reason",
)
REQUIRED = {
    "create": {"task", "due"},
    "reschedule": {"due", "reminder_ref"},
    "snooze": {"reminder_ref", "snooze_minutes"},
    "clarify": {"question"},
    "refuse": {"refusal_reason"},
}
OPTIONAL = {"reschedule": {"task"}}


@dataclass(frozen=True)
class DecisionOutput:
    """One decision; fields that do not apply to it are always ``None``."""

    decision: str
    task: str | None = None
    due: str | None = None
    reminder_ref: str | None = None
    snooze_minutes: int | None = None
    question: str | None = None
    refusal_reason: str | None = None

    def __post_init__(self) -> None:
        """Enforce the per-decision required and null rules."""
        if self.decision not in DECISIONS:
            raise ValueError("unknown decision")
        values = self.to_dict()
        required = REQUIRED[self.decision]
        allowed = required | OPTIONAL.get(self.decision, set())
        for key in OUTPUT_KEYS[1:]:
            present = values[key] is not None
            if key in required and not present:
                raise ValueError(f"{self.decision} requires {key}")
            if present and key not in allowed:
                raise ValueError(f"{self.decision} must not set {key}")
        if self.refusal_reason is not None and self.refusal_reason not in (
            REFUSAL_REASONS
        ):
            raise ValueError("unknown refusal reason")
        minutes = self.snooze_minutes
        if minutes is not None and (isinstance(minutes, bool) or minutes < 1):
            raise ValueError("snooze_minutes must be a whole number >= 1")

    def to_dict(self) -> dict[str, object]:
        """Return all seven keys in schema order."""
        values = asdict(self)
        return {key: values[key] for key in OUTPUT_KEYS}

    def to_json(self) -> str:
        """Return the decision as one JSON object with no surrounding text."""
        return json.dumps(self.to_dict(), ensure_ascii=False)
