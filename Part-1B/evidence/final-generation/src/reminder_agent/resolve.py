"""Turn an interpreted time into an exact instant (research R3; FR-006, FR-008).

The model names a local wall time or a duration; this module does all arithmetic,
attaches the request timezone's offset at the due instant (INV-007), and turns
non-existent, ambiguous or past times into a clarifying question (PROP-001).
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from reminder_agent.interpretation import Interpretation

ASK_TIME = "When should I remind you?"
ASK_PAST = "That time has already passed. When should I remind you instead?"
ASK_GAP = "That clock time is skipped by the daylight-saving change. Which time works?"
ASK_FOLD = "That clock time happens twice because of daylight saving. Which one?"


@dataclass(frozen=True)
class Resolution:
    """Either an exact due instant or the question to ask instead."""

    due: datetime | None = None
    question: str | None = None


def _attach_zone(wall: datetime, zone: ZoneInfo) -> Resolution:
    first = wall.replace(tzinfo=zone, fold=0)
    second = wall.replace(tzinfo=zone, fold=1)
    round_trip = first.astimezone(UTC).astimezone(zone).replace(tzinfo=None)
    if round_trip != wall:
        return Resolution(question=ASK_GAP)
    if first.utcoffset() != second.utcoffset():
        return Resolution(question=ASK_FOLD)
    return Resolution(due=first)


def resolve_due(interp: Interpretation, now: datetime, zone: ZoneInfo) -> Resolution:
    """Resolve the interpretation's time against the injected ``now`` and ``zone``."""
    if interp.relative_minutes is not None:
        # Add elapsed time in UTC: aware-datetime arithmetic in a zone is wall-clock
        # and would ignore a DST transition between now and the due instant.
        elapsed = timedelta(minutes=interp.relative_minutes)
        resolution = Resolution(due=now.astimezone(UTC) + elapsed)
    elif interp.due_local is not None:
        resolution = _attach_zone(datetime.fromisoformat(interp.due_local), zone)
    else:
        return Resolution(question=ASK_TIME)
    if resolution.due is None:
        return resolution
    if resolution.due < now:
        return Resolution(question=ASK_PAST)
    return Resolution(due=resolution.due.astimezone(zone))


def format_due(due: datetime) -> str:
    """Serialise a due instant as ``YYYY-MM-DDTHH:MM:SS±HH:MM``."""
    return due.replace(microsecond=0).isoformat(timespec="seconds")
