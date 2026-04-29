from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import BackgroundTask

TASK_PENDING = "pending"
TASK_RUNNING = "running"
TASK_COMPLETED = "completed"
TASK_FAILED = "failed"
TASK_CANCELLED = "cancelled"

INTERRUPTED_TASK_ERROR = "Task interrupted by local process restart"


class BackgroundTaskService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        project_id: str,
        task_type: str,
        payload: dict | None = None,
    ) -> BackgroundTask:
        task = BackgroundTask(
            project_id=project_id,
            task_type=task_type,
            payload=payload or {},
            status=TASK_PENDING,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: str) -> BackgroundTask:
        task = self.db.query(BackgroundTask).filter(BackgroundTask.id == task_id).first()
        if not task:
            raise ValueError(f"Background task not found: {task_id}")
        return task

    def list_for_project(self, project_id: str, limit: int = 20) -> list[BackgroundTask]:
        return (
            self.db.query(BackgroundTask)
            .filter(BackgroundTask.project_id == project_id)
            .order_by(BackgroundTask.created_at.desc())
            .limit(limit)
            .all()
        )

    def mark_running(self, task_id: str) -> BackgroundTask:
        task = self.get(task_id)
        task.status = TASK_RUNNING
        task.started_at = task.started_at or datetime.now(UTC)
        task.error = None
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_completed(self, task_id: str, result: dict | None = None) -> BackgroundTask:
        task = self.get(task_id)
        task.status = TASK_COMPLETED
        task.result = result or {}
        task.error = None
        task.finished_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_failed(self, task_id: str, error: str) -> BackgroundTask:
        task = self.get(task_id)
        task.status = TASK_FAILED
        task.error = error
        task.finished_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(task)
        return task

    def mark_cancelled(self, task_id: str, reason: str | None = None) -> BackgroundTask:
        task = self.get(task_id)
        task.status = TASK_CANCELLED
        task.error = reason
        task.finished_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(task)
        return task

    def fail_interrupted_running_tasks(self) -> int:
        tasks = self.db.query(BackgroundTask).filter(BackgroundTask.status == TASK_RUNNING).all()
        now = datetime.now(UTC)
        for task in tasks:
            task.status = TASK_FAILED
            task.error = INTERRUPTED_TASK_ERROR
            task.finished_at = now
        self.db.commit()
        return len(tasks)

