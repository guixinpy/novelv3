from pydantic import BaseModel, Field

from .dialog import ProjectDiagnosisOut
from .outline import OutlineOut
from .project import ProjectOut
from .setup import SetupOut
from .storyline import StorylineOut
from .version import VersionSummary


class ChapterSummaryOut(BaseModel):
    id: str
    chapter_index: int
    title: str
    word_count: int = 0
    status: str = "generated"


class DialogBootstrapOut(BaseModel):
    messages: list[dict] = Field(default_factory=list)


class WorkspaceBootstrapOut(BaseModel):
    project: ProjectOut
    diagnosis: ProjectDiagnosisOut
    setup: SetupOut | None = None
    storyline: StorylineOut | None = None
    outline: OutlineOut | None = None
    chapters: list[ChapterSummaryOut] = Field(default_factory=list)
    versions: list[VersionSummary] = Field(default_factory=list)
    dialogs: dict[str, DialogBootstrapOut] = Field(default_factory=dict)
