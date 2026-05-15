from fastapi import FastAPI, HTTPException

from models import JobRequest, JobResponse
from services.job_service import JobManager

app = FastAPI(title="Task API")


@app.post("/create", response_model=JobResponse)
def create_job(request: JobRequest) -> JobResponse:
    return JobManager.create_job(request)


@app.get("/status/{job_id}", response_model=JobResponse)
def read_job_status(job_id: str) -> JobResponse:
    job = JobManager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/status")
def status() -> dict[str, str]:
    return {"status": "ok"}
