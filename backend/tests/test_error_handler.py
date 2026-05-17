import httpx
import pytest

from app.core.error_handler import AppError, with_retry


def _status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("POST", "https://api.deepseek.com/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_non_retryable_http_status():
    attempts = 0
    error = _status_error(400)

    async def fail_bad_request():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await with_retry(fail_bad_request, max_attempts=3, base_delay=0)

    assert exc_info.value is error
    assert attempts == 1


@pytest.mark.asyncio
async def test_with_retry_retries_rate_limit_and_server_errors():
    attempts = 0
    errors = [_status_error(429), _status_error(500)]

    async def flaky_transient():
        nonlocal attempts
        attempts += 1
        if errors:
            raise errors.pop(0)
        return "ok"

    result = await with_retry(flaky_transient, max_attempts=3, base_delay=0)

    assert result == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_with_retry_does_not_retry_app_errors():
    attempts = 0
    error = AppError("PARSE_ERROR", "无法解析模型返回的 JSON")

    async def fail_app_error():
        nonlocal attempts
        attempts += 1
        raise error

    with pytest.raises(AppError) as exc_info:
        await with_retry(fail_app_error, max_attempts=3, base_delay=0)

    assert exc_info.value is error
    assert attempts == 1
