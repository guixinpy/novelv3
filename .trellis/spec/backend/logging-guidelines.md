# Logging Guidelines

> How logging is done in this project.

---

## Overview

Logging uses a lightweight structured-event function `log_event()` defined in
`app/core/local_diagnostics.py`. There is no heavy logging framework — events
are dicts with structured fields, written to local diagnostics output.

---

## Core Function

```python
# app/core/local_diagnostics.py
def log_event(event_type: str, **fields) -> None:
    """Emit a structured diagnostic event."""
    entry = {
        "event": event_type,
        "timestamp": datetime.now(UTC).isoformat(),
        **fields,
    }
    print(json.dumps(entry), file=sys.stderr)
```

All events are JSON lines written to stderr. This keeps them out of stdout
(which may carry API responses) while remaining visible in server logs.

---

## Log Levels

The project does not use traditional log levels. Instead, `log_event()` uses
the event type for semantic categorization:

| Category | Event type prefix | Example |
|----------|-----------------|---------|
| Request tracking | `request_done` | `log_event("request_done", request_id=..., status=200, ...)` |
| Background tasks | `background_tasks_*` | `log_event("background_tasks_interrupted", marked_failed=5)` |
| Agent events | `agent_*` | `log_event("agent_turn", session_id=..., tool_calls=3)` |

---

## Structured Fields

Every event should include:

| Field | Required | Description |
|-------|----------|-------------|
| `request_id` | For request-scoped events | Unique per-request ID |
| `duration_ms` | For performance events | Wall-clock time in ms |
| `error` | On error events | String representation of the error |
| `status` | For HTTP events | HTTP status code |

Request-scoped fields are set via the diagnostics middleware in `app/main.py`:

```python
response.headers["X-Request-ID"] = request_id
log_event("request_done", request_id=request_id, method=request.method,
          path=request.url.path, status=response.status_code,
          duration_ms=elapsed_ms)
```

---

## What to Log

- **Every HTTP request**: method, path, status code, duration, request_id
- **Background task lifecycle**: startup, interrupted, completion state
- **Agent turn boundaries**: session_id, tool count, iteration budget
- **API key resolution**: success or failure (without logging the key itself)
- **Unexpected errors**: full error message with request_id context

---

## What NOT to Log

- **API keys, tokens, or secrets**: Never log `DEEPSEEK_API_KEY` or similar.
- **Full request/response bodies**: They may contain user content (novel text).
- **Database connection strings with credentials**: Log only the scheme, not the full URL.
- **Personal user data**: Project names and genre are public; avoid logging user-identifying fields.

---

## Common Mistakes

1. **Logging to stdout** — Use stderr for diagnostic events so they don't
   interfere with API response output.
2. **Missing request_id** — Without it, correlating logs across requests is
   impossible.
3. **Logging PII** — User-written novel content should never appear in logs.
4. **Inconsistent event names** — Use `snake_case` for event types and field names.
