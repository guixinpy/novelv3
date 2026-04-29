from typing import Any

from pydantic import BaseModel, Field


class AthenaRetrievalIndexResult(BaseModel):
    status: str
    project_id: str
    chapter_index: int | None = None
    indexed: dict[str, int]


class AthenaRetrievalDiagnostics(BaseModel):
    project_id: str
    embedding_provider: str
    embedding_model: str
    vector_dimension: int
    total_documents: int
    total_chunks: int
    total_terms: int
    total_embeddings: int
    documents_by_source_type: dict[str, int]


class AthenaRetrievalSearchItem(BaseModel):
    chunk_id: str
    document_id: str
    source_type: str
    source_ref: str
    title: str
    chapter_index: int | None = None
    score: float
    lexical_score: float
    vector_score: float
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AthenaRetrievalSearchResponse(BaseModel):
    query: str
    total: int
    items: list[AthenaRetrievalSearchItem]
