# Longform Scale Phase 307 - Reset Cached AI Adapters After Key Rotation

## Goal

Keep long-running writing sessions recoverable when the user updates the DeepSeek API key without restarting the server.

## Finding

`AIService` cached the DeepSeek adapter after first use. The config endpoint saved a new API key but did not reset existing adapters, so subsequent generation could keep using the old key until process restart.

## TDD Evidence

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_config.py -q
```

Observed failure:

```text
assert service._adapter is None
E AssertionError: assert <AsyncMock ...> is None
```

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_config.py -q
```

Observed result:

```text
5 passed
```

## Change

- `AIService` now tracks live service instances with a weak registry.
- The config update endpoint closes cached adapters after saving the new key.
- The next generation call rebuilds its adapter through `load_api_key()`.

## Verification

Full phase gate:

- `backend\.venv\Scripts\python.exe -m pytest backend\tests -q` -> `703 passed`
- `npm run build` -> passed
- `npm run test:unit -- --run` -> `441 passed`
- `git diff --check` -> passed
- DeepSeek key scan -> `NO_MATCH`
