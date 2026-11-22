# Contract: Model Client

## Protocol (`src/reminder_agent/ports.py`)

```text
class ModelClient(Protocol):
    def generate(self, system: str, user: str, response_schema: Mapping[str, object]) -> str: ...
```

Returns the model's reply text (possibly empty) or raises one of the typed errors below. No
parsing, prompt text or decision logic in any implementation.

## GeminiClient (`src/reminder_agent/model_client.py`, the only network module)

- Constructor: `GeminiClient(api_key, model="gemini-2.5-flash", timeout_seconds=30.0,
  connection_factory=<HTTPSConnection factory>)`; `GeminiClient.from_env(environ)` reads
  `GEMINI_API_KEY` (required), `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`.
  `connection_factory(host: str, timeout: float)` returns an object with `request(method, url,
  body, headers)`, `getresponse()` (→ `.status`, `.read()`) and `close()`; tests inject a stub.
  The key never appears in `repr()` or error messages.
- Request: `POST /v1beta/models/{model}:generateContent` on host
  `generativelanguage.googleapis.com`, TLS via `ssl.create_default_context()`.
  Headers `Content-Type: application/json`, `x-goog-api-key`.
  Body:

  ```json
  {
    "systemInstruction": {"parts": [{"text": "<system>"}]},
    "contents": [{"role": "user", "parts": [{"text": "<user>"}]}],
    "generationConfig": {
      "temperature": 0, "candidateCount": 1,
      "responseMimeType": "application/json", "responseSchema": {"...": "..."}
    }
  }
  ```

- Response: concatenated `candidates[0].content.parts[*].text`; empty string when absent.

## Error mapping

| Condition | Raised |
|---|---|
| timeout on connect/read | `ModelTimeout` |
| HTTP 429 | `ModelRateLimited` |
| HTTP 500/502/503/504, connection/transport failure, non-JSON 200 body | `ModelUnavailable` |
| missing key; HTTP 400/401/403/404 | `ModelConfigError` |
| any other non-200 | `ModelUnavailable` |

Error messages carry the status code and error type only; never the key, headers or body.

## FakeModelClient (tests)

Records each `(system, user, response_schema)` call and returns the next scripted string or
raises the next scripted exception.
