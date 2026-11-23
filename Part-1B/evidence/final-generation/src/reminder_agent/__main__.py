"""CLI: one JSON request on stdin, one decision on stdout (contracts/agent-api.md)."""

import json
import os
import sys
from collections.abc import Callable, Mapping
from typing import TextIO

from reminder_agent.agent import handle_request
from reminder_agent.errors import (
    InvalidModelOutput,
    InvalidRequest,
    ModelConfigError,
    ModelRateLimited,
    ModelTimeout,
    ModelUnavailable,
)
from reminder_agent.model_client import GeminiClient
from reminder_agent.ports import ModelClient
from reminder_agent.request import Request

EXIT_OK = 0
EXIT_INPUT = 2
EXIT_SERVICE = 3
EXIT_OUTPUT = 4
REQUEST_FIELDS = ("text", "now", "timezone")

ClientFactory = Callable[[Mapping[str, str]], ModelClient]


def _read_request(stdin: TextIO) -> Request:
    try:
        data = json.loads(stdin.read())
    except ValueError as exc:
        raise InvalidRequest("stdin is not JSON") from exc
    if not isinstance(data, dict) or any(key not in data for key in REQUEST_FIELDS):
        raise InvalidRequest("request needs text, now and timezone")
    return Request(text=data["text"], now=data["now"], timezone=data["timezone"])


def _fail(stderr: TextIO, error: Exception, code: int) -> int:
    stderr.write(f"error: {type(error).__name__}\n")
    return code


def main(
    stdin: TextIO,
    stdout: TextIO,
    stderr: TextIO,
    environ: Mapping[str, str],
    client_factory: ClientFactory,
) -> int:
    """Run one request; return the exit code defined in the contract."""
    try:
        request = _read_request(stdin)
        client = client_factory(environ)
    except (InvalidRequest, ModelConfigError) as exc:
        return _fail(stderr, exc, EXIT_INPUT)
    secrets = [environ.get("GEMINI_API_KEY", "")]
    try:
        decision = handle_request(request, client, secrets=secrets)
    except ModelConfigError as exc:
        return _fail(stderr, exc, EXIT_INPUT)
    except (ModelTimeout, ModelRateLimited, ModelUnavailable) as exc:
        return _fail(stderr, exc, EXIT_SERVICE)
    except InvalidModelOutput as exc:
        return _fail(stderr, exc, EXIT_OUTPUT)
    stdout.write(decision.to_json() + "\n")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main(sys.stdin, sys.stdout, sys.stderr, os.environ, GeminiClient.from_env))
