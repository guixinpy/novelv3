import asyncio

import httpx


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


async def with_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            if attempt == max_attempts or not is_retryable_error(exc):
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))


def is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, AppError):
        return False
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code == 429 or status_code >= 500
    if isinstance(exc, httpx.RequestError):
        return True
    return True
