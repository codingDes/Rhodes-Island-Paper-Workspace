from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    content_type: str
    size_bytes: int
    storage_path: str
    text_length: int
    title_candidate: str
    preview: str
    parsed_text_path: str


class SummaryResponse(BaseModel):
    doc_id: str
    source: str
    title_candidate: str
    topic: str
    research_question: str
    core_method: str
    innovations: list[str]
    experiment_results: str
    limitations: str
    plain_explanation: str
    llm_error: Optional[str] = None


class ChatRequest(BaseModel):
    question: str
    operator_id: str = "amiya"
    focus_doc_ids: list[str] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)


class ChatResponse(BaseModel):
    doc_id: str
    focus_doc_ids: list[str] = Field(default_factory=list)
    source: str
    operator_id: str
    operator_name: str
    answer: str
    sanity_effect: str = "restore"
    sanity_delta: int = 0
    tool_used: Optional[str] = None
    llm_error: Optional[str] = None


class LoreEntryPayload(BaseModel):
    title: str = ""
    content: str = ""


class OperatorLorePayload(BaseModel):
    entries: list[LoreEntryPayload] = Field(default_factory=list)


class GlobalLorePayload(BaseModel):
    content: str = ""


class ArchiveItem(BaseModel):
    doc_id: str
    filename: str = ""
    title: str = ""
    categories: list[str] = Field(default_factory=list)
    text_length: int = 0


class ArchiveStatePayload(BaseModel):
    categories: list[str] = Field(default_factory=list)
    archives: list[ArchiveItem] = Field(default_factory=list)


class ArchiveStateResponse(BaseModel):
    categories: list[str] = Field(default_factory=list)
    archives: list[ArchiveItem] = Field(default_factory=list)

