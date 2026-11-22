"""Type and value checks shared by the configuration and the limiter.

Every check raises ``TypeError`` for a value of the wrong type and ``ValueError``
for a value of the right type that is out of range. Every message starts with
the field name followed by ``": "``. ``bool`` is never accepted as a number.
"""

from fractions import Fraction


def _type_name(value: object) -> str:
    """Return the name of the type of ``value``, for error messages.

    Args:
        value: Any object.

    Returns:
        The ``__name__`` of the type of ``value``.
    """
    return type(value).__name__


def require_int(field: str, value: object) -> int:
    """Return ``value`` if it is an ``int`` that is not a ``bool``.

    Args:
        field: Field name used as the message prefix.
        value: The value to check.

    Returns:
        The value, unchanged.

    Raises:
        TypeError: If ``value`` is not an ``int`` or is a ``bool``.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"{field}: must be int, got {_type_name(value)}"
        raise TypeError(msg)
    return value


def require_rational(field: str, value: object) -> int | Fraction:
    """Return ``value`` if it is an ``int`` or a ``Fraction`` and not a ``bool``.

    Args:
        field: Field name used as the message prefix.
        value: The value to check.

    Returns:
        The value, unchanged.

    Raises:
        TypeError: If ``value`` is not an ``int`` or ``Fraction``, or is a ``bool``.
    """
    if isinstance(value, bool) or not isinstance(value, int | Fraction):
        msg = f"{field}: must be int or Fraction, got {_type_name(value)}"
        raise TypeError(msg)
    return value


def require_positive(field: str, value: int | Fraction) -> None:
    """Check that a number is strictly greater than zero.

    Args:
        field: Field name used as the message prefix.
        value: The number to check.

    Raises:
        ValueError: If ``value`` is zero or negative.
    """
    if value <= 0:
        msg = f"{field}: must be > 0, got {value}"
        raise ValueError(msg)


def require_nonempty_str(field: str, value: object) -> str:
    """Return ``value`` if it is a non-empty ``str``.

    Args:
        field: Field name used as the message prefix.
        value: The value to check.

    Returns:
        The value, unchanged.

    Raises:
        TypeError: If ``value`` is not a ``str``.
        ValueError: If ``value`` is the empty string.
    """
    if not isinstance(value, str):
        msg = f"{field}: must be str, got {_type_name(value)}"
        raise TypeError(msg)
    if not value:
        msg = f"{field}: must not be empty"
        raise ValueError(msg)
    return value


def require_nonempty_tuple_of[T](
    field: str, value: object, kind: type[T]
) -> tuple[T, ...]:
    """Return ``value`` as a non-empty tuple whose items are all of type ``kind``.

    A ``list`` is accepted and converted to a tuple; any other container type
    is rejected.

    Args:
        field: Field name used as the message prefix.
        value: The tuple (or list) to check.
        kind: The type every item must have.

    Returns:
        The items as a tuple, in their original order.

    Raises:
        TypeError: If ``value`` is not a tuple or list, or an item is not ``kind``.
        ValueError: If ``value`` is empty.
    """
    if not isinstance(value, tuple | list):
        msg = f"{field}: must be a tuple of {kind.__name__}, got {_type_name(value)}"
        raise TypeError(msg)
    if not value:
        msg = f"{field}: must contain at least one {kind.__name__}"
        raise ValueError(msg)
    items: list[T] = []
    for index, item in enumerate(value):
        if not isinstance(item, kind):
            msg = (
                f"{field}: item {index} must be {kind.__name__}, got {_type_name(item)}"
            )
            raise TypeError(msg)
        items.append(item)
    return tuple(items)
