from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.chapter_target import chapter_index_exceeds_target
from app.models import ChapterContent, Project, WritingState
from app.schemas import WritingStateOut


class WritingStateService:
    def __init__(self, db: Session):
        self.db = db

    def start(self, project_id: str) -> WritingStateOut:
        state = self._get(project_id)
        if state is None:
            state = WritingState(
                project_id=project_id,
                current_chapter=self._next_chapter_index(project_id),
                status="idle",
            )
            self.db.add(state)
            self.db.flush()
        state.status = "running"
        state.current_chapter = state.current_chapter or self._next_chapter_index(project_id)
        state.last_error = None
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def pause(self, project_id: str) -> WritingStateOut:
        state = self._get(project_id)
        if not state:
            return self._default(project_id)
        state.status = "paused"
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def resume(self, project_id: str) -> WritingStateOut:
        state = self._get(project_id)
        if not state:
            return self._default(project_id)
        state.status = "running"
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def run_chapter(self, project_id: str, chapter_index: int) -> WritingStateOut:
        state = self._get_or_create(project_id)
        state.status = "running"
        state.current_chapter = max(int(state.current_chapter or 0), int(chapter_index))
        state.last_error = None
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def complete_chapter(self, project_id: str, chapter_index: int) -> WritingStateOut:
        state = self._get_or_create(project_id)
        previous_status = state.status
        state.current_chapter = max(int(state.current_chapter or 0), int(chapter_index) + 1)
        project = self.db.query(Project).filter(Project.id == project_id).first()
        completed = bool(project and chapter_index_exceeds_target(self.db, project, state.current_chapter))
        if completed:
            state.status = "completed"
        elif previous_status == "paused":
            state.status = "paused"
        else:
            state.status = "idle"
        if project and completed:
            project.status = "completed"
            project.current_phase = "content"
        state.last_error = None
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def finish_project(self, project_id: str) -> WritingStateOut:
        state = self._get_or_create(project_id)
        project = self.db.query(Project).filter(Project.id == project_id).first()
        state.status = "completed"
        state.last_error = None
        state.updated_at = datetime.now(UTC)
        if project:
            project.status = "completed"
            project.current_phase = "content"
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def reconcile_target(self, project_id: str) -> WritingStateOut:
        state = self._get(project_id)
        if not state:
            return self._default(project_id)
        project = self.db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return self._out(state)

        previous_status = state.status
        next_status = state.status
        if chapter_index_exceeds_target(self.db, project, state.current_chapter):
            next_status = "completed"
        elif state.status == "completed":
            next_status = "idle"

        changed = False
        if next_status != state.status:
            state.status = next_status
            state.last_error = None
            state.updated_at = datetime.now(UTC)
            changed = True

        if self._sync_project_completion(project, previous_status, next_status):
            changed = True

        if not changed:
            return self._out(state)

        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def state(self, project_id: str) -> WritingStateOut:
        state = self._get(project_id)
        if not state:
            return self._default(project_id)
        return self._out(state)

    def mark_error(self, project_id: str, error: str) -> WritingStateOut:
        state = self._get_or_create(project_id)
        state.status = "failed"
        state.last_error = error
        state.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(state)
        return self._out(state)

    def _get(self, project_id: str) -> WritingState | None:
        return self.db.query(WritingState).filter(WritingState.project_id == project_id).first()

    def _get_or_create(self, project_id: str) -> WritingState:
        state = self._get(project_id)
        if state:
            return state
        state = WritingState(project_id=project_id, current_chapter=1, status="idle")
        self.db.add(state)
        self.db.flush()
        return state

    def _next_chapter_index(self, project_id: str) -> int:
        latest = (
            self.db.query(func.max(ChapterContent.chapter_index))
            .filter(ChapterContent.project_id == project_id, ChapterContent.content != "")
            .scalar()
        )
        return int(latest or 0) + 1

    @staticmethod
    def _default(project_id: str) -> WritingStateOut:
        return WritingStateOut(project_id=project_id, current_chapter=1, status="idle")

    @staticmethod
    def _out(state: WritingState) -> WritingStateOut:
        return WritingStateOut(
            project_id=state.project_id,
            current_chapter=state.current_chapter,
            status=state.status,
            last_error=state.last_error,
        )

    @staticmethod
    def _sync_project_completion(project: Project, previous_status: str, next_status: str) -> bool:
        if next_status == "completed":
            changed = project.status != "completed" or project.current_phase != "content"
            project.status = "completed"
            project.current_phase = "content"
            return changed
        if previous_status == "completed" and next_status != "completed":
            changed = project.status != "writing" or project.current_phase != "content"
            project.status = "writing"
            project.current_phase = "content"
            return changed
        return False
