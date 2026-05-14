from app.schemas import WritingStateOut
from app.services.writing.writing_state_service import WritingStateService


class WritingScheduler:
    def start(self, project_id: str, db) -> WritingStateOut:
        return WritingStateService(db).start(project_id)

    def pause(self, project_id: str, db) -> WritingStateOut:
        return WritingStateService(db).pause(project_id)

    def resume(self, project_id: str, db) -> WritingStateOut:
        return WritingStateService(db).resume(project_id)

    def run_chapter(self, project_id: str, chapter_index: int, db) -> WritingStateOut:
        return WritingStateService(db).run_chapter(project_id, chapter_index)

    def state(self, project_id: str, db) -> WritingStateOut:
        return WritingStateService(db).state(project_id)
