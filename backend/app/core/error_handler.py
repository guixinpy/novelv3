import asyncio


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 500):
        self.code = code
        self.status_code = status_code
        super().__init__(message)


async def with_retry(fn, max_attempts: int = 3, base_delay: float = 1.0):
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except Exception:
            if attempt == max_attempts:
                raise
            await asyncio.sleep(base_delay * (2 ** (attempt - 1)))
