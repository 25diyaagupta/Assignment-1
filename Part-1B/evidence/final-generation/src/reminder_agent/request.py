"""The validated request (data-model.md §Request; FR-001, FR-003)."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from reminder_agent.errors import InvalidRequest


def _parse_now(value: object) -> datetime:
    if not isinstance(value, str):
        raise InvalidRequest("now must be a string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise InvalidRequest("now is not an ISO 8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise InvalidRequest("now must carry a UTC offset")
    return parsed


def _load_zone(value: object) -> ZoneInfo:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRequest("timezone must be a non-empty IANA name")
    try:
        return ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, OSError) as exc:
        raise InvalidRequest("timezone is not a known IANA name") from exc


@dataclass(frozen=True)
class Request:
    """Free text plus the injected ``now`` and IANA ``timezone``."""

    text: str
    now: str
    timezone: str

    def __post_init__(self) -> None:
        """Validate the request before any model call (FR-003)."""
        if not isinstance(self.text, str):
            raise InvalidRequest("text must be a string")
        _parse_now(self.now)
        _load_zone(self.timezone)

    @property
    def zone(self) -> ZoneInfo:
        """The request timezone."""
        return _load_zone(self.timezone)

    @property
    def now_local(self) -> datetime:
        """The supplied now, expressed in the request timezone."""
        return _parse_now(self.now).astimezone(self.zone)
