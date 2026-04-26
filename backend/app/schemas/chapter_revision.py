from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RevisionAnnotationIn(BaseModel):
    paragraph_index: int = Field(ge=0)
    start_offset: int = Field(ge=0)
    end_offset: int = Field(ge=0)
    selected_text: str = Field(min_length=1)
    comment: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.end_offset <= self.start_offset:
            raise ValueError("end_offset must be greater than start_offset")
        return self


class RevisionCorrectionIn(BaseModel):
    paragraph_index: int = Field(ge=0)
    original_text: str = Field(min_length=1)
    corrected_text: str = Field(min_length=1)


class ChapterRevisionCreate(BaseModel):
    chapter_index: int = Field(ge=1)
    annotations: list[RevisionAnnotationIn] = Field(default_factory=list)
    corrections: list[RevisionCorrectionIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_feedback(self):
        if not self.annotations and not self.corrections:
            raise ValueError("revision feedback cannot be empty")
        return self


class ChapterRevisionDraftUpdate(BaseModel):
    annotations: list[RevisionAnnotationIn] = Field(default_factory=list)
    corrections: list[RevisionCorrectionIn] = Field(default_factory=list)


class RevisionAnnotationOut(BaseModel):
    id: str
    revision_id: str
    paragraph_index: int
    start_offset: int
    end_offset: int
    selected_text: str
    comment: str

    model_config = ConfigDict(from_attributes=True)


class RevisionCorrectionOut(BaseModel):
    id: str
    revision_id: str
    paragraph_index: int
    original_text: str
    corrected_text: str

    model_config = ConfigDict(from_attributes=True)


class ChapterRevisionOut(BaseModel):
    id: str
    project_id: str
    chapter_id: str
    chapter_index: int
    revision_index: int
    status: str
    submitted_at: datetime | None
    completed_at: datetime | None
    base_version_id: str | None
    result_version_id: str | None
    annotations: list[RevisionAnnotationOut]
    corrections: list[RevisionCorrectionOut]

    model_config = ConfigDict(from_attributes=True)
