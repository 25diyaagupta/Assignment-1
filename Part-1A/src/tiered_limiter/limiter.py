"""The tiered token-bucket limiter and its decision type.

``TieredLimiter`` is not thread-safe: the caller must serialise access to one
instance.
"""

from dataclasses import dataclass
from fractions import Fraction

from tiered_limiter._validate import (
    require_int,
    require_nonempty_str,
    require_positive,
    require_rational,
)
from tiered_limiter.bucket import BucketState, consume, full, refill, wait_for
from tiered_limiter.clock import Clock
from tiered_limiter.config import LimiterConfig, Tier
from tiered_limiter.errors import CostExceedsCapacityError, UnknownTierError


@dataclass(frozen=True, slots=True)
class Decision:
    """The result of one call to ``TieredLimiter.acquire``.

    Attributes:
        allowed: ``True`` if the cost was taken from every limit of the tier.
        retry_after: ``0`` when allowed; when denied, the exact seconds until
            the same request could be allowed.
    """

    allowed: bool
    retry_after: int | Fraction


class TieredLimiter:
    """Decides requests against the limits of named tiers.

    State is kept per ``(client_key, tier_name)`` pair and created lazily,
    full, on the first ``acquire``. Time comes only from the injected clock.
    This class is not thread-safe.
    """

    def __init__(self, config: LimiterConfig, clock: Clock) -> None:
        """Create a limiter.

        Args:
            config: The validated limiter configuration.
            clock: The clock that supplies every reading.

        Raises:
            TypeError: If ``config`` is not a ``LimiterConfig`` or ``clock``
                has no callable ``now``.
        """
        if not isinstance(config, LimiterConfig):
            msg = f"config: must be LimiterConfig, got {type(config).__name__}"
            raise TypeError(msg)
        if not callable(getattr(clock, "now", None)):
            msg = "clock: must have a callable now()"
            raise TypeError(msg)
        self._tiers: dict[str, Tier] = {tier.name: tier for tier in config.tiers}
        self._clock = clock
        self._states: dict[tuple[str, str], tuple[BucketState, ...]] = {}

    def acquire(self, client_key: str, tier_name: str, cost: int = 1) -> Decision:
        """Decide one request and take its cost from every limit if allowed.

        Args:
            client_key: Non-empty client identifier.
            tier_name: Name of a configured tier.
            cost: Tokens the request costs (``int`` > 0, at most every capacity).

        Returns:
            The decision. A denied request takes nothing from any limit.

        Raises:
            TypeError: If an input or the clock reading has the wrong type.
            ValueError: If an input is empty or not positive.
            UnknownTierError: If ``tier_name`` is not configured.
            CostExceedsCapacityError: If ``cost`` exceeds a limit's capacity.
        """
        tier = self._resolve(client_key, tier_name)
        self._check_cost(tier, cost)
        now = self._read_clock()
        states = self._current(client_key, tier, now)
        key = (client_key, tier.name)
        if all(state.balance >= cost for state in states):
            self._states[key] = tuple(consume(state, cost) for state in states)
            return Decision(allowed=True, retry_after=0)
        self._states[key] = states
        waits = [
            wait_for(state, limit, cost)
            for state, limit in zip(states, tier.limits, strict=True)
        ]
        return Decision(allowed=False, retry_after=max(waits))

    def inspect(self, client_key: str, tier_name: str) -> tuple[int | Fraction, ...]:
        """Return the client's balances refilled to the current reading.

        Nothing is stored and no state is created.

        Args:
            client_key: Non-empty client identifier.
            tier_name: Name of a configured tier.

        Returns:
            One balance per limit, in the tier's limit order. A client that has
            not been seen gets the full capacities.

        Raises:
            TypeError: If an input or the clock reading has the wrong type.
            ValueError: If an input is empty.
            UnknownTierError: If ``tier_name`` is not configured.
        """
        tier = self._resolve(client_key, tier_name)
        now = self._read_clock()
        return tuple(state.balance for state in self._current(client_key, tier, now))

    def _resolve(self, client_key: object, tier_name: object) -> Tier:
        """Validate the client key and tier name and return the tier.

        Args:
            client_key: The client key to check.
            tier_name: The tier name to check and look up.

        Returns:
            The configured tier.

        Raises:
            TypeError: If either value is not a ``str``.
            ValueError: If either value is empty.
            UnknownTierError: If the tier is not configured.
        """
        require_nonempty_str("client_key", client_key)
        name = require_nonempty_str("tier_name", tier_name)
        tier = self._tiers.get(name)
        if tier is None:
            msg = f"tier_name: unknown tier {name!r}"
            raise UnknownTierError(msg)
        return tier

    @staticmethod
    def _check_cost(tier: Tier, cost: object) -> None:
        """Validate the cost against its type, sign and every capacity.

        Args:
            tier: The tier whose limits the cost must fit.
            cost: The cost to check.

        Raises:
            TypeError: If ``cost`` is not an ``int`` or is a ``bool``.
            ValueError: If ``cost`` is zero or negative.
            CostExceedsCapacityError: If ``cost`` exceeds a limit's capacity.
        """
        value = require_int("cost", cost)
        require_positive("cost", value)
        for limit in tier.limits:
            if value > limit.capacity:
                msg = (
                    f"cost: {value} exceeds capacity {limit.capacity} "
                    f"of a limit in tier {tier.name!r}"
                )
                raise CostExceedsCapacityError(msg)

    def _read_clock(self) -> int | Fraction:
        """Read the clock once and check the reading's type.

        Returns:
            The reading, as an ``int`` or ``Fraction``.

        Raises:
            TypeError: If the reading is not an ``int`` or ``Fraction``.
        """
        return require_rational("clock reading", self._clock.now())

    def _current(
        self, client_key: str, tier: Tier, now: int | Fraction
    ) -> tuple[BucketState, ...]:
        """Return the client's states for the tier refilled to ``now``.

        Nothing is stored; a client that has not been seen gets full buckets.

        Args:
            client_key: The validated client key.
            tier: The resolved tier.
            now: The validated clock reading.

        Returns:
            One state per limit, in the tier's limit order.
        """
        stored = self._states.get((client_key, tier.name))
        if stored is None:
            return tuple(full(limit, now) for limit in tier.limits)
        return tuple(
            refill(state, limit, now)
            for state, limit in zip(stored, tier.limits, strict=True)
        )
