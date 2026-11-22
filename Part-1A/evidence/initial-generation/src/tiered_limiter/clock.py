"""Clock protocol and the production monotonic clock.

This is the only module in the package that reads the system clock. Every other
module receives the current reading through an injected ``Clock``.
"""

import time
from fractions import Fraction
from typing import Protocol

_NANOSECONDS_PER_SECOND = 10**9


class Clock(Protocol):
    """A source of the current reading, in seconds, as an exact rational."""

    def now(self) -> int | Fraction:
        """Return the current reading in seconds.

        Returns:
            The reading as an ``int`` or a ``Fraction``.
        """


class MonotonicClock:
    """Production clock backed by the system monotonic counter."""

    def now(self) -> Fraction:
        """Return the monotonic reading in seconds as an exact ``Fraction``.

        Returns:
            ``Fraction(time.monotonic_ns(), 10**9)``.
        """
        return Fraction(time.monotonic_ns(), _NANOSECONDS_PER_SECOND)
