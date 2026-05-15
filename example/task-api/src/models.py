from typing import Any

from pydantic import BaseModel


class JobRequest(BaseModel):
    file_path: str
    callback_url: str | None = None
    metadata: dict[str, Any] | None = None


class JobResponse(BaseModel):
    job_id: str
    job_status: str
    file_path: str
    result_info: dict[str, Any] | None = None
    created_at: str | None = None
    updated_at: str | None = None
