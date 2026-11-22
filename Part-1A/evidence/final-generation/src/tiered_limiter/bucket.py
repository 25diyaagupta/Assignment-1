"""Token-bucket state and its pure transitions.

All arithmetic is exact: balances, readings and waits are ``int`` or
``Fraction``.
"""

from dataclasses import dataclass
from fractions import Fraction

from tiered_limiter.config import Limit


@dataclass(frozen=True, slots=True)
class BucketState:
    """One client's balance for one limit.

    Attributes:
        balance: Tokens available, with ``0 <= balance <= capacity``.
        last_seen: Latest clock reading applied; it never decreases.
    """

    balance: int | Fraction
    last_seen: int | Fraction


def full(limit: Limit, now: int | Fraction) -> BucketState:
    """Return the state of a new bucket, which starts full.

    Args:
        limit: The limit the bucket belongs to.
        now: The current clock reading.

    Returns:
        A state holding ``limit.capacity`` tokens, last seen at ``now``.
    """
    return BucketState(balance=limit.capacity, last_seen=now)


def refill(state: BucketState, limit: Limit, now: int | Fraction) -> BucketState:
    """Return the state refilled up to ``now``.

    A reading earlier than ``last_seen`` counts as zero elapsed seconds, and
    ``last_seen`` never moves backwards.

    Args:
        state: The current state.
        limit: The limit the bucket belongs to.
        now: The current clock reading.

    Returns:
        The refilled state, capped at ``limit.capacity``.
    """
    elapsed = max(0, now - state.last_seen)
    balance = min(limit.capacity, state.balance + elapsed * limit.refill_rate)
    return BucketState(balance=balance, last_seen=max(state.last_seen, now))


def consume(state: BucketState, cost: int) -> BucketState:
    """Return the state with ``cost`` tokens taken.

    The caller must only call this when ``state.balance >= cost``.

    Args:
        state: The current state.
        cost: The number of tokens to take.

    Returns:
        The state with the reduced balance.
    """
    return BucketState(balance=state.balance - cost, last_seen=state.last_seen)


def wait_for(state: BucketState, limit: Limit, cost: int) -> int | Fraction:
    """Return the exact seconds until the bucket holds ``cost`` tokens.

    Args:
        state: The current (already refilled) state.
        limit: The limit the bucket belongs to.
        cost: The number of tokens wanted.

    Returns:
        ``0`` if the balance already covers the cost, otherwise
        ``(cost - balance) / refill_rate`` as a ``Fraction``.
    """
    if state.balance >= cost:
        return 0
    return Fraction(cost - state.balance) / limit.refill_rate
