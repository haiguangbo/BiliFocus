from pydantic import BaseModel, Field

from app.schemas.video import VideoItem


class PipelineStageTrace(BaseModel):
    agent: str
    status: str
    summary: str
    outputs: list[str] = Field(default_factory=list)


class CurationPipelineTrace(BaseModel):
    planner: PipelineStageTrace
    reviewer: PipelineStageTrace
    classifier: PipelineStageTrace


class CurationRunRequest(BaseModel):
    objective: str = Field(min_length=1)
    extra_requirements: str | None = None
    max_keywords: int = Field(default=5, ge=1, le=10)
    limit_per_keyword: int = Field(default=8, ge=1, le=20)
    sync_accepted: bool = True


class CurationRunResponse(BaseModel):
    job_id: str
    status: str
    objective: str
    recommended_keywords: list[str]
    pipeline_trace: CurationPipelineTrace
    reviewed_count: int
    accepted_count: int
    rejected_count: int
    saved_count: int
    skipped_count: int
    accepted_items: list[VideoItem]
    started_at: str
    finished_at: str


class CurationJobCreateResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress_message: str


class CurationJobStatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str
    progress_message: str
    result: CurationRunResponse | None = None
    error_message: str | None = None
