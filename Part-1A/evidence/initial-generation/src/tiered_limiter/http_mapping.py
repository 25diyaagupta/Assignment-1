"""Map a limiter decision to an HTTP status and headers.

Named ``http_mapping`` so that it does not shadow the standard library ``http``.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass

from tiered_limiter.limiter import Decision

_STATUS_OK = 200
_STATUS_TOO_MANY_REQUESTS = 429
_MIN_RETRY_AFTER_SECONDS = 1


@dataclass(frozen=True, slots=True)
class HttpOutcome:
    """The HTTP status and headers for one decision.

    Attributes:
        status: ``200`` when allowed, ``429`` when denied.
        headers: ``{}`` for 200; ``{"Retry-After": "<digits>"}`` for 429.
    """

    status: int
    headers: Mapping[str, str]


def to_http(decision: Decision) -> HttpOutcome:
    """Turn a decision into an HTTP outcome.

    Args:
        decision: The limiter decision.

    Returns:
        ``HttpOutcome(200, {})`` when allowed; otherwise ``HttpOutcome(429,
        {"Retry-After": str(max(1, ceil(retry_after)))})``.
    """
    if decision.allowed:
        return HttpOutcome(status=_STATUS_OK, headers={})
    seconds = max(_MIN_RETRY_AFTER_SECONDS, math.ceil(decision.retry_after))
    return HttpOutcome(
        status=_STATUS_TOO_MANY_REQUESTS,
        headers={"Retry-After": str(seconds)},
    )
