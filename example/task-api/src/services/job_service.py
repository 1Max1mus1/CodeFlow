from datetime import datetime
from uuid import uuid4

from models import JobRequest, JobResponse


class JobManager:
    _jobs: dict[str, JobResponse] = {}

    @classmethod
    def create_job(cls, request: JobRequest) -> JobResponse:
        cls._validate_job_request(request)
        job_id = str(uuid4())
        created = datetime.utcnow().isoformat()
        cls._update_job_status(job_id, "queued")
        blob_url = cls._upload_to_blob(request.file_path)
        result = cls._process_pdf(request.file_path)
        job = JobResponse(
            job_id=job_id,
            job_status="completed",
            file_path=blob_url,
            result_info=result,
            created_at=created,
            updated_at=datetime.utcnow().isoformat(),
        )
        cls._jobs[job_id] = job
        return job

    @classmethod
    def get_job(cls, job_id: str) -> JobResponse | None:
        cls._update_job_status(job_id, "read")
        return cls._jobs.get(job_id)

    @classmethod
    def _process_pdf(cls, file_path: str) -> dict[str, str]:
        cls._update_job_status(file_path, "processing")
        cls._upload_to_blob(file_path)
        return {"summary": "processed", "source": file_path}

    @classmethod
    def _update_job_status(cls, job_id: str, status: str) -> None:
        existing = cls._jobs.get(job_id)
        if existing is not None:
            cls._jobs[job_id] = existing.model_copy(
                update={
                    "job_status": status,
                    "updated_at": datetime.utcnow().isoformat(),
                }
            )

    @classmethod
    def _upload_to_blob(cls, file_path: str) -> str:
        return f"blob://jobs/{file_path}"

    @classmethod
    def _validate_job_request(cls, request: JobRequest) -> None:
        if not request.file_path:
            raise ValueError("file_path is required")
