import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.db import SessionLocal
from app.models import BackgroundTask
from app.services.tasks.background_task_service import BackgroundTaskService

TaskWork = Callable[[Session, BackgroundTask], Awaitable[dict | None] | dict | None]


class LocalTaskRunner:
    def __init__(self, session_factory: sessionmaker = SessionLocal):
        self.session_factory = session_factory

    def start(self, task_id: str, work: TaskWork) -> asyncio.Task:
        return asyncio.create_task(self.run_now(task_id, work))

    async def run_now(self, task_id: str, work: TaskWork) -> dict | None:
        db = self.session_factory()
        service = BackgroundTaskService(db)
        try:
            task = service.mark_running(task_id)
            result = work(db, task)
            if inspect.isawaitable(result):
                result = await result
            service.mark_completed(task_id, result if isinstance(result, dict) else {})
            return result
        except Exception as exc:
            service.mark_failed(task_id, str(exc))
            raise
        finally:
            db.close()
