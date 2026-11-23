"""The ModelClient protocol every module receives (constitution I)."""

from collections.abc import Mapping
from typing import Protocol


class ModelClient(Protocol):
    """Sends one prompt to a language model and returns its raw reply text."""

    def generate(
        self, system: str, user: str, response_schema: Mapping[str, object]
    ) -> str:
        """Return the model reply text, or raise a ``ModelError`` subclass."""
        ...
