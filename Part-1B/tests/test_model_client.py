"""GeminiClient HTTP shape and error mapping (contracts/model-client.md)."""

from __future__ import annotations

import http.client
import json

import pytest

from reminder_agent.errors import (
    ModelConfigError,
    ModelRateLimited,
    ModelTimeout,
    ModelUnavailable,
)
from reminder_agent.model_client import GeminiClient

PLACEHOLDER = "-".join(["placeholder", "credential", "for", "tests"])
HOST = "generativelanguage.googleapis.com"
SCHEMA = {"type": "OBJECT", "properties": {"decision": {"type": "STRING"}}}


class StubResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = body

    def read(self):
        return self._body


class StubConnection:
    def __init__(self, status=200, body=b"", exc=None, request_exc=None):
        self.status = status
        self.body = body
        self.exc = exc
        self.request_exc = request_exc
        self.sent = None
        self.closed = False

    def request(self, method, url, body=None, headers=None):
        if self.request_exc is not None:
            raise self.request_exc
        self.sent = {
            "method": method,
            "url": url,
            "body": body,
            "headers": headers or {},
        }

    def getresponse(self):
        if self.exc is not None:
            raise self.exc
        return StubResponse(self.status, self.body)

    def close(self):
        self.closed = True


def reply_body(*texts):
    parts = [{"text": text} for text in texts]
    return json.dumps({"candidates": [{"content": {"parts": parts}}]}).encode()


def make_client(connection, **kwargs):
    opened = []

    def factory(host, timeout):
        opened.append((host, timeout))
        return connection

    client = GeminiClient(PLACEHOLDER, connection_factory=factory, **kwargs)
    return client, opened


@pytest.mark.covers("FR-001")
def test_request_shape():
    connection = StubConnection(body=reply_body('{"decision": "clarify"}'))
    client, opened = make_client(
        connection, model="gemini-test-model", timeout_seconds=12.5
    )
    text = client.generate("SYSTEM TEXT", "USER TEXT", SCHEMA)
    assert text == '{"decision": "clarify"}'
    assert opened == [(HOST, 12.5)]
    sent = connection.sent
    assert sent["method"] == "POST"
    assert sent["url"] == "/v1beta/models/gemini-test-model:generateContent"
    assert PLACEHOLDER not in sent["url"]
    headers = {key.lower(): value for key, value in sent["headers"].items()}
    assert headers["x-goog-api-key"] == PLACEHOLDER
    assert headers["content-type"] == "application/json"
    body = json.loads(sent["body"])
    assert body["systemInstruction"]["parts"][0]["text"] == "SYSTEM TEXT"
    assert body["contents"][0]["parts"][0]["text"] == "USER TEXT"
    assert body["contents"][0]["role"] == "user"
    config = body["generationConfig"]
    assert config["temperature"] == 0
    assert config["responseMimeType"] == "application/json"
    assert config["responseSchema"] == SCHEMA
    assert connection.closed is True


@pytest.mark.covers("FR-001")
def test_reply_parts_are_joined():
    client, _ = make_client(StubConnection(body=reply_body('{"a":', " 1}")))
    assert client.generate("s", "u", SCHEMA) == '{"a": 1}'


@pytest.mark.covers("FR-022")
def test_no_candidates_returns_empty_string():
    body = json.dumps({"promptFeedback": {"blockReason": "SAFETY"}}).encode()
    client, _ = make_client(StubConnection(body=body))
    assert client.generate("s", "u", SCHEMA) == ""


@pytest.mark.covers("FR-022")
@pytest.mark.parametrize(
    ("connection", "error"),
    [
        (StubConnection(exc=TimeoutError("read timed out")), ModelTimeout),
        (StubConnection(request_exc=TimeoutError("connect timed out")), ModelTimeout),
        (StubConnection(status=429, body=b"{}"), ModelRateLimited),
        (StubConnection(status=500, body=b"{}"), ModelUnavailable),
        (StubConnection(status=502, body=b"{}"), ModelUnavailable),
        (StubConnection(status=503, body=b"{}"), ModelUnavailable),
        (StubConnection(status=504, body=b"{}"), ModelUnavailable),
        (StubConnection(status=418, body=b"{}"), ModelUnavailable),
        (StubConnection(request_exc=OSError("connection refused")), ModelUnavailable),
        (
            StubConnection(exc=http.client.RemoteDisconnected("closed")),
            ModelUnavailable,
        ),
        (StubConnection(status=200, body=b"not json"), ModelUnavailable),
        (StubConnection(status=400, body=b"{}"), ModelConfigError),
        (StubConnection(status=401, body=b"{}"), ModelConfigError),
        (StubConnection(status=403, body=b"{}"), ModelConfigError),
        (StubConnection(status=404, body=b"{}"), ModelConfigError),
    ],
)
def test_error_mapping(connection, error):
    client, _ = make_client(connection)
    with pytest.raises(error) as caught:
        client.generate("s", "u", SCHEMA)
    assert PLACEHOLDER not in str(caught.value)


@pytest.mark.covers("FR-022")
def test_from_env_requires_key():
    with pytest.raises(ModelConfigError):
        GeminiClient.from_env({})
    with pytest.raises(ModelConfigError):
        GeminiClient.from_env({"GEMINI_API_KEY": ""})


@pytest.mark.covers("FR-022")
def test_from_env_defaults_and_overrides():
    defaults = GeminiClient.from_env(
        {
            "GEMINI_API_KEY": PLACEHOLDER,
            "GEMINI_MODEL": "",
            "GEMINI_TIMEOUT_SECONDS": "",
        }
    )
    assert defaults.model == "gemini-2.5-flash"
    assert defaults.timeout_seconds == 30.0
    custom = GeminiClient.from_env(
        {
            "GEMINI_API_KEY": PLACEHOLDER,
            "GEMINI_MODEL": "m-1",
            "GEMINI_TIMEOUT_SECONDS": "5",
        }
    )
    assert custom.model == "m-1"
    assert custom.timeout_seconds == 5.0
    assert PLACEHOLDER not in repr(custom)
