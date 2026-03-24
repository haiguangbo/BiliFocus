from __future__ import annotations

from threading import Lock, Thread

from app.schemas.curation import CurationJobCreateResponse, CurationJobStatusResponse, CurationRunRequest


class CurationJobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, CurationJobStatusResponse] = {}

    def create(self, *, job_id: str) -> CurationJobCreateResponse:
        snapshot = CurationJobStatusResponse(
            job_id=job_id,
            status="queued",
            stage="planner",
            progress_message="任务已创建，等待执行",
        )
        with self._lock:
            self._jobs[job_id] = snapshot
        return CurationJobCreateResponse(
            job_id=job_id,
            status=snapshot.status,
            stage=snapshot.stage,
            progress_message=snapshot.progress_message,
        )

    def update(self, job_id: str, *, status: str, stage: str, progress_message: str) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(
                update={
                    "status": status,
                    "stage": stage,
                    "progress_message": progress_message,
                }
            )

    def complete(self, job_id: str, result) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(
                update={
                    "status": "completed",
                    "stage": "completed",
                    "progress_message": "已完成本次 AI 策展",
                    "result": result,
                }
            )

    def fail(self, job_id: str, message: str) -> None:
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = current.model_copy(
                update={
                    "status": "failed",
                    "stage": current.stage,
                    "progress_message": "AI 策展执行失败",
                    "error_message": message,
                }
            )

    def get(self, job_id: str) -> CurationJobStatusResponse | None:
        with self._lock:
            return self._jobs.get(job_id)


job_store = CurationJobStore()


def start_curation_job(
    *,
    job_id: str,
    payload: CurationRunRequest,
    runner,
) -> CurationJobCreateResponse:
    response = job_store.create(job_id=job_id)

    def task() -> None:
        try:
            job_store.update(job_id, status="running", stage="planner", progress_message="正在规划关键词")
            result = runner(payload, job_id)
            job_store.complete(job_id, result)
        except Exception as exc:
            job_store.fail(job_id, str(exc))

    Thread(target=task, daemon=True).start()
    return response
