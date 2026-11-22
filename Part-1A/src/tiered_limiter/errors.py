"""Domain-specific errors raised by the limiter."""


class UnknownTierError(ValueError):
    """Raised when a request names a tier that is not configured."""


class CostExceedsCapacityError(ValueError):
    """Raised when a request cost is larger than the capacity of a tier limit."""
