# Contract: Agent API and CLI

## Library

```text
handle_request(request: Request, client: ModelClient, *, secrets: Sequence[str] = ()) -> DecisionOutput
Request(text: str, now: str, timezone: str)       # validated on construction → InvalidRequest
DecisionOutput.to_dict() -> dict                   # seven keys, per Output Schema
DecisionOutput.to_json() -> str                    # one JSON object, no surrounding text
```

- Exactly one `client.generate(...)` call per valid request; zero for an invalid one.
- Raises `InvalidRequest` (input), `ModelTimeout` / `ModelRateLimited` / `ModelUnavailable` /
  `ModelConfigError` (service, passed through unchanged), `InvalidModelOutput` (unusable reply).
- Never reads the wall clock or environment; `secrets` (values the leak guard must never emit)
  are passed in by the caller.
- Output validates against [output.schema.json](output.schema.json).

## CLI

```text
python -m reminder_agent  < request.json  > decision.json
```

- stdin: `{"text": "...", "now": "2026-03-04T10:00:00+05:30", "timezone": "Asia/Kolkata"}`
- stdout: one decision object. Builds `GeminiClient` from the environment (`GEMINI_API_KEY`,
  `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`) and passes the key as a secret to the guard.
- Exit codes: `0` decision written; `2` invalid request or config error; `3` service error;
  `4` invalid model output. Errors go to stderr as one line naming the error type, never the key.
