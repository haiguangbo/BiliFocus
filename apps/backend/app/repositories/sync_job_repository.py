from app.models.sync_job import SyncJob
from sqlalchemy.orm import Session


class SyncJobRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_job(
        self,
        *,
        job_id: str,
        query: str,
        filter_text: str | None,
        source: str,
        status: str,
        started_at: str,
    ) -> SyncJob:
        job = SyncJob(
            job_id=job_id,
            query=query,
            filter_text=filter_text,
            source=source,
            status=status,
            saved_count=0,
            skipped_count=0,
            failed_count=0,
            started_at=started_at,
        )
        self.db.add(job)
        return job

    def complete_job(
        self,
        job: SyncJob,
        *,
        status: str,
        saved_count: int,
        skipped_count: int,
        failed_count: int,
        finished_at: str,
        error_message: str | None = None,
    ) -> SyncJob:
        job.status = status
        job.saved_count = saved_count
        job.skipped_count = skipped_count
        job.failed_count = failed_count
        job.finished_at = finished_at
        job.error_message = error_message
        return job
