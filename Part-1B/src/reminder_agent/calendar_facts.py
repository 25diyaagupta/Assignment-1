"""Calendar facts derived only from the injected now and timezone (research R3)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from reminder_agent.request import Request

WEEKDAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
UPCOMING_DAYS = 14


def format_offset(moment: datetime) -> str:
    """Return the UTC offset of an aware datetime as ``+HH:MM``."""
    offset = moment.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "-" if minutes < 0 else "+"
    hours, rest = divmod(abs(minutes), 60)
    return f"{sign}{hours:02d}:{rest:02d}"


@dataclass(frozen=True)
class CalendarFacts:
    """Local date, weekday, offset and the following 14 dates (data-model.md)."""

    local_now: datetime
    weekday: str
    offset: str
    upcoming: tuple[tuple[str, str], ...]


def calendar_facts(request: Request) -> CalendarFacts:
    """Compute calendar facts for a request; never reads the wall clock."""
    local_now = request.now_local
    today = local_now.date()
    upcoming = tuple(
        (
            (today + timedelta(days=step)).isoformat(),
            WEEKDAYS[(today + timedelta(days=step)).weekday()],
        )
        for step in range(1, UPCOMING_DAYS + 1)
    )
    return CalendarFacts(
        local_now=local_now,
        weekday=WEEKDAYS[today.weekday()],
        offset=format_offset(local_now),
        upcoming=upcoming,
    )


def describe(facts: CalendarFacts) -> str:
    """Render the facts as plain lines for the model."""
    lines = [
        f"Today: {facts.local_now.date().isoformat()} {facts.weekday}",
        f"Local time now: {facts.local_now.strftime('%H:%M')}",
        f"Current UTC offset: {facts.offset}",
        "Upcoming dates:",
    ]
    for index, (day, name) in enumerate(facts.upcoming):
        label = " (tomorrow)" if index == 0 else ""
        lines.append(f"- {day} {name}{label}")
    return "\n".join(lines)
