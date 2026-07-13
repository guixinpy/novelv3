# Error Handling

> How errors are handled in this project.

---

## Overview

The project uses a layered error handling strategy:

1. **Custom exceptions** (`AppError`) for business logic errors
2. **`with_retry` decorator** for transient LLM/network failures
3. **FastAPI `HTTPException`** for API-level errors
4. **Diagnostics middleware** for request-level error tracking

---

## Error Types

### AppError (business logic errors)

Defined in `app/core/error_handler.py`:

```python
class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
```

Usage: Raise in core/service logic when a business rule is violated.
These are **never retried** — they represent deterministic rejection.

### HTTPException (API-level errors)

Used directly in route handlers for missing resources or bad requests:

```python
raise HTTPException(status_code=404, detail="project not found")
raise HTTPException(status_code=409, detail="chapter already published")
```

---

## Retry Pattern

`async def with_retry()` in `app/core/error_handler.py` implements exponential
backoff for transient failures:

```python
async def with_retry(coro_factory, max_retries=3, base_delay=1.0):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if exc.response.status_code not in (429, 502, 503, 504):
                raise  # non-retryable status
            last_exc = exc
            await asyncio.sleep(base_delay * (2 ** attempt))
    raise last_exc
```

**Retryable**: 429, 502, 503, 504, transport errors
**Non-retryable**: 4xx (except 429), `AppError`, validation errors

---

## API Error Responses

All unexpected errors flow through the diagnostics middleware in `app/main.py`:

```python
@app.middleware("http")
async def local_request_diagnostics(request, call_next):
    request_id = new_request_id()
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:
        log_event("request_done",
            request_id=request_id, method=request.method,
            path=request.url.path, status=500,
            duration_ms=int((time.perf_counter() - started) * 1000),
            error=str(exc))
        raise
    response.headers["X-Request-ID"] = request_id
    log_event("request_done",
        request_id=request_id, method=request.method,
        path=request.url.path, status=response.status_code,
        duration_ms=int((time.perf_counter() - started) * 1000))
    return response
```

Every request gets an `X-Request-ID` header for traceability.

---

## Service Layer Error Handling

Services catch and wrap errors rather than letting them propagate raw:

```python
class SomeService:
    def __init__(self, db: Session):
        self.db = db

    def do_something(self, project_id: str):
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise AppError(code="project_not_found",
                           message=f"Project {project_id} not found",
                           status_code=404)
```

---

## Common Mistakes

1. **Swallowing exceptions in with_retry** — Non-retryable errors (4xx except 429)
   must be re-raised immediately, not retried.
2. **Missing `request_id` on error logs** — Always include request_id in error
   context for debugging.
3. **Raising `HTTPException` in service/core layer** — Use `AppError` there;
   let the route handler translate to `HTTPException` if needed.
4. **Forgetting `JSON` decode error handling** — `res.json()` in client code
   should have a fallback, as some error responses may not be valid JSON.
