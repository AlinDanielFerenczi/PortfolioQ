import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

_executor = ThreadPoolExecutor(max_workers=4)
_jobs: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def submit_job(method: str, fn: Callable, *args, **kwargs) -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "method": method,
            "status": "pending",
            "submitted_at": _now(),
            "completed_at": None,
            "result": None,
            "error": None,
        }

    def _run():
        with _lock:
            _jobs[job_id]["status"] = "running"
        try:
            result = fn(*args, **kwargs)
            with _lock:
                _jobs[job_id]["status"] = "completed"
                _jobs[job_id]["result"] = result
                _jobs[job_id]["completed_at"] = _now()
        except Exception as e:
            with _lock:
                _jobs[job_id]["status"] = "failed"
                _jobs[job_id]["error"] = str(e)
                _jobs[job_id]["completed_at"] = _now()

    _executor.submit(_run)
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job is not None else None
