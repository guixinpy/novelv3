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

    def create_chapter_range(
        self,
        *,
        project_id: str,
        task_type: str,
        start_chapter_index: int,
        end_chapter_index: int,
        payload: dict | None = None,
        idempotency_key: str | None = None,
    ) -> BackgroundTask:
        if start_chapter_index < 1 or end_chapter_index < start_chapter_index:
            raise ValueError("chapter range must start at 1 or later and end after start")
        next_payload = dict(payload or {})
        next_payload["chapter_range"] = {"start": start_chapter_index, "end": end_chapter_index}
        if idempotency_key:
            next_payload["idempotency_key"] = idempotency_key
        return self.create(project_id=project_id, task_type=task_type, payload=next_payload)

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

    def mark_range_progress(self, task_id: str, *, completed_chapter_index: int) -> BackgroundTask:
        task = self.get(task_id)
        start, end = _task_chapter_range(task)
        if completed_chapter_index < start or completed_chapter_index > end:
            raise ValueError(f"completed chapter {completed_chapter_index} is outside task range {start}-{end}")

        result = dict(task.result or {})
        progress = dict(result.get("progress") or {})
        completed = set(progress.get("completed_chapter_indexes") or [])
        completed.add(completed_chapter_index)
        completed_indexes = sorted({int(index) for index in completed if start <= int(index) <= end})
        next_chapter_index = next((index for index in range(start, end + 1) if index not in completed_indexes), end + 1)
        progress = {
            "chapter_range": {"start": start, "end": end},
            "completed_chapter_indexes": completed_indexes,
            "next_chapter_index": next_chapter_index,
            "completed_count": len(completed_indexes),
            "total_count": end - start + 1,
            "can_resume": next_chapter_index <= end,
        }
        result["progress"] = progress
        task.result = result
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

    def create_retry_from_failed(self, task_id: str) -> BackgroundTask:
        task = self.get(task_id)
        if task.status not in {TASK_FAILED, TASK_CANCELLED}:
            raise ValueError(f"background task {task_id} is {task.status} and cannot be retried")
        start, _end = _task_chapter_range(task)
        progress = (task.result or {}).get("progress") or {}
        resume_from = int(progress.get("next_chapter_index") or start)
        payload = dict(task.payload or {})
        payload["retry_of_task_id"] = task.id
        payload["resume_from_chapter_index"] = resume_from
        return self.create(project_id=task.project_id, task_type=task.task_type, payload=payload)

    def fail_interrupted_running_tasks(self) -> int:
        tasks = self.db.query(BackgroundTask).filter(BackgroundTask.status == TASK_RUNNING).all()
        now = datetime.now(UTC)
        for task in tasks:
            task.status = TASK_FAILED
            task.error = INTERRUPTED_TASK_ERROR
            task.finished_at = now
        self.db.commit()
        return len(tasks)


def _task_chapter_range(task: BackgroundTask) -> tuple[int, int]:
    chapter_range = (task.payload or {}).get("chapter_range")
    if not isinstance(chapter_range, dict):
        raise ValueError(f"background task {task.id} does not define a chapter range")
    start = int(chapter_range.get("start") or 0)
    end = int(chapter_range.get("end") or 0)
    if start < 1 or end < start:
        raise ValueError(f"background task {task.id} has invalid chapter range")
    return start, end
