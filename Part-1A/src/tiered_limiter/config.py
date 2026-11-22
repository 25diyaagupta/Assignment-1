"""Immutable configuration: limits, tiers and the whole limiter configuration.

Every class validates its fields when it is constructed and raises
``TypeError`` or ``ValueError`` with a message that starts with the field name.
"""

from dataclasses import dataclass
from fractions import Fraction

from tiered_limiter._validate import (
    require_int,
    require_nonempty_str,
    require_nonempty_tuple_of,
    require_positive,
    require_rational,
)


@dataclass(frozen=True, slots=True)
class Limit:
    """One token-bucket rule.

    Attributes:
        capacity: Maximum number of tokens the bucket holds (``int`` > 0).
        refill_rate: Tokens added per second (``int`` or ``Fraction`` > 0).
    """

    capacity: int
    refill_rate: int | Fraction

    def __post_init__(self) -> None:
        """Validate the capacity and the refill rate.

        Raises:
            TypeError: If a field has the wrong type (``bool`` included).
            ValueError: If a field is zero or negative.
        """
        require_int("capacity", self.capacity)
        require_positive("capacity", self.capacity)
        require_rational("refill_rate", self.refill_rate)
        require_positive("refill_rate", self.refill_rate)


@dataclass(frozen=True, slots=True)
class Tier:
    """A named set of limits; a request must satisfy every one of them.

    Attributes:
        name: Non-empty tier name.
        limits: One or more ``Limit`` objects, in a fixed order.
    """

    name: str
    limits: tuple[Limit, ...]

    def __post_init__(self) -> None:
        """Validate the name and the limits, and store the limits as a tuple.

        Raises:
            TypeError: If the name is not a ``str`` or an item is not a ``Limit``.
            ValueError: If the name is empty or there are no limits.
        """
        require_nonempty_str("name", self.name)
        limits = require_nonempty_tuple_of("limits", self.limits, Limit)
        object.__setattr__(self, "limits", limits)


@dataclass(frozen=True, slots=True)
class LimiterConfig:
    """The whole limiter configuration.

    Attributes:
        tiers: One or more ``Tier`` objects with unique names.
    """

    tiers: tuple[Tier, ...]

    def __post_init__(self) -> None:
        """Validate the tiers, check that names are unique, and store a tuple.

        Raises:
            TypeError: If an item is not a ``Tier``.
            ValueError: If there are no tiers or two tiers share a name.
        """
        tiers = require_nonempty_tuple_of("tiers", self.tiers, Tier)
        seen: set[str] = set()
        for tier in tiers:
            if tier.name in seen:
                msg = f"tiers: duplicate tier name {tier.name!r}"
                raise ValueError(msg)
            seen.add(tier.name)
        object.__setattr__(self, "tiers", tiers)
