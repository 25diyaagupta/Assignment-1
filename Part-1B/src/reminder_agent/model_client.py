"""Gemini REST client: the only module that talks to the network (constitution I).

It sends a prompt and returns raw reply text or a typed error (research R1, R2, R5).
It holds no prompt text, no parsing beyond extracting the reply text, and no
decision logic.
"""

import http.client
import json
import ssl
from collections.abc import Callable, Mapping
from typing import Protocol
from urllib.parse import quote

from reminder_agent.errors import (
    ModelConfigError,
    ModelRateLimited,
    ModelTimeout,
    ModelUnavailable,
)

HOST = "generativelanguage.googleapis.com"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_TIMEOUT_SECONDS = 30.0
HTTP_OK = 200
RATE_LIMITED = frozenset({429})
CONFIG_ERRORS = frozenset({400, 401, 403, 404})


class _Response(Protocol):
    status: int

    def read(self) -> bytes: ...


class _Connection(Protocol):
    def request(
        self, method: str, url: str, body: bytes, headers: Mapping[str, str]
    ) -> None: ...

    def getresponse(self) -> _Response: ...

    def close(self) -> None: ...


ConnectionFactory = Callable[[str, float], _Connection]


def https_connection(host: str, timeout: float) -> http.client.HTTPSConnection:
    """Open a verified TLS connection with the configured timeout."""
    context = ssl.create_default_context()
    return http.client.HTTPSConnection(host, timeout=timeout, context=context)


def _raise_for_status(status: int) -> None:
    if status == HTTP_OK:
        return
    if status in RATE_LIMITED:
        raise ModelRateLimited(f"HTTP {status}")
    if status in CONFIG_ERRORS:
        raise ModelConfigError(f"HTTP {status}")
    raise ModelUnavailable(f"HTTP {status}")


def _reply_text(payload: bytes) -> str:
    try:
        data = json.loads(payload)
    except (TypeError, ValueError) as exc:
        raise ModelUnavailable("response body is not JSON") from exc
    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list) or not candidates:
        return ""
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return ""
    texts = [
        part["text"]
        for part in parts
        if isinstance(part, dict) and isinstance(part.get("text"), str)
    ]
    return "".join(texts)


class GeminiClient:
    """ModelClient for the Gemini ``generateContent`` REST endpoint."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        connection_factory: ConnectionFactory = https_connection,
    ) -> None:
        """Store configuration; the key is kept private and never printed."""
        if not api_key:
            raise ModelConfigError("GEMINI_API_KEY is not set")
        self._api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self._connection_factory = connection_factory

    def __repr__(self) -> str:
        """Describe the client without the key."""
        return f"GeminiClient(model={self.model!r}, timeout={self.timeout_seconds})"

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "GeminiClient":
        """Build a client from GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TIMEOUT_SECONDS."""
        api_key = environ.get("GEMINI_API_KEY", "").strip()
        model = environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        raw_timeout = environ.get("GEMINI_TIMEOUT_SECONDS", "").strip()
        try:
            timeout = float(raw_timeout) if raw_timeout else DEFAULT_TIMEOUT_SECONDS
        except ValueError as exc:
            raise ModelConfigError("GEMINI_TIMEOUT_SECONDS is not a number") from exc
        if timeout <= 0:
            raise ModelConfigError("GEMINI_TIMEOUT_SECONDS must be positive")
        return cls(api_key, model=model, timeout_seconds=timeout)

    def generate(
        self, system: str, user: str, response_schema: Mapping[str, object]
    ) -> str:
        """Send one prompt and return the reply text (empty if there is none)."""
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0,
                "candidateCount": 1,
                "responseMimeType": "application/json",
                "responseSchema": dict(response_schema),
            },
        }
        status, payload = self._post(json.dumps(body).encode("utf-8"))
        _raise_for_status(status)
        return _reply_text(payload)

    def _post(self, body: bytes) -> tuple[int, bytes]:
        path = f"/v1beta/models/{quote(self.model, safe='-._')}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }
        connection = self._connection_factory(HOST, self.timeout_seconds)
        try:
            connection.request("POST", path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        except TimeoutError as exc:
            raise ModelTimeout("the model service timed out") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise ModelUnavailable(type(exc).__name__) from exc
        finally:
            connection.close()
