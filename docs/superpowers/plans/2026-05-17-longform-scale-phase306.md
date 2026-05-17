# Longform Scale Phase 306 - Avoid Retrying Non-Recoverable Model Errors

## Goal

Keep long-running generation loops from wasting time on errors that cannot recover through retry.

## Finding

`with_retry()` retried every exception. For long-form continuous writing, a permanent model/API problem such as HTTP 400/401/403 or a local `AppError` would be retried repeatedly, delaying the actual failure and making configuration or prompt issues harder to diagnose.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_error_handler.py -q
```

Observed failure:

```text
assert attempts == 1
E assert 3 == 1
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_error_handler.py -q
```

Observed result:

```text
3 passed
```

## Change

- `AppError` is not retried.
- HTTP 4xx errors are not retried except `429` rate limiting.
- HTTP 5xx and `httpx.RequestError` network/transport failures remain retryable.
- Unknown exceptions retain the previous retry behavior.

## Verification

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `702 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `441 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
