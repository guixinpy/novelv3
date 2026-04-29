import asyncio
import inspect
from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session, sessionmaker

from app.db import SessionLocal
from app.core.local_diagnostics import duration_ms_since, log_event, now_ms
from app.models import BackgroundTask
from app.services.tasks.background_task_service import BackgroundTaskService

TaskWork = Callable[[Session, BackgroundTask], Awaitable[dict | None] | dict | None]


class LocalTaskRunner:
    def __init__(self, session_factory: sessionmaker = SessionLocal):
        self.session_factory = session_factory

    def start(self, task_id: str, work: TaskWork) -> asyncio.Task:
        return asyncio.create_task(self.run_now(task_id, work))

    async def run_now(self, task_id: str, work: TaskWork) -> dict | None:
        started_ms = now_ms()
        db = self.session_factory()
        service = BackgroundTaskService(db)
        try:
            task = service.mark_running(task_id)
            result = work(db, task)
            if inspect.isawaitable(result):
                result = await result
            service.mark_completed(task_id, result if isinstance(result, dict) else {})
            log_event(
                "task_done",
                task_id=task.id,
                task_type=task.task_type,
                project_id=task.project_id,
                status="completed",
                duration_ms=duration_ms_since(started_ms),
            )
            return result
        except Exception as exc:
            service.mark_failed(task_id, str(exc))
            log_event(
                "task_failed",
                task_id=task_id,
                status="failed",
                error=str(exc),
                duration_ms=duration_ms_since(started_ms),
            )
            raise
        finally:
            db.close()
