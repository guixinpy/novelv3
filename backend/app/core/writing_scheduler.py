from app.schemas import WritingStateOut


class WritingScheduler:
    def __init__(self):
        self._states: dict[str, dict] = {}

    def start(self, project_id: str) -> WritingStateOut:
        self._states[project_id] = {
            "project_id": project_id,
            "current_chapter": 1,
            "status": "running",
            "last_error": None,
        }
        return WritingStateOut(**self._states[project_id])

    def pause(self, project_id: str) -> WritingStateOut:
        if project_id in self._states:
            self._states[project_id]["status"] = "paused"
        return WritingStateOut(**self._states.get(project_id, {"project_id": project_id, "current_chapter": 1, "status": "idle"}))

    def resume(self, project_id: str) -> WritingStateOut:
        if project_id in self._states:
            self._states[project_id]["status"] = "running"
        return WritingStateOut(**self._states.get(project_id, {"project_id": project_id, "current_chapter": 1, "status": "idle"}))

    def state(self, project_id: str) -> WritingStateOut:
        return WritingStateOut(**self._states.get(project_id, {"project_id": project_id, "current_chapter": 1, "status": "idle"}))
