"""Leak guard: output never carries instructions, the marker or secrets (PROP-004)."""

import re
from collections.abc import Iterable, Sequence

MARKER_LINE = re.compile(r"^Marker:\s*(\S+)\s*$", re.MULTILINE)
MIN_RUN_CHARS = 40


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def find_marker(system_text: str) -> str | None:
    """Return the marker planted in the system instructions, if any."""
    match = MARKER_LINE.search(system_text)
    return match.group(1) if match else None


def _shares_run(text: str, reference: str, run: int) -> bool:
    if len(reference) < run:
        return False
    return any(text[i : i + run] in reference for i in range(len(text) - run + 1))


def leaks(
    texts: Iterable[str],
    system_text: str,
    secrets: Sequence[str],
    run: int = MIN_RUN_CHARS,
) -> bool:
    """Return True if any text contains the marker, a secret or a prompt run."""
    reference = _normalise(system_text)
    marker = find_marker(system_text)
    for text in texts:
        if any(secret and secret in text for secret in secrets):
            return True
        normalised = _normalise(text)
        if marker and marker.lower() in normalised:
            return True
        if _shares_run(normalised, reference, run):
            return True
    return False
