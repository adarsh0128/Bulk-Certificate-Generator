from __future__ import annotations

import time

from app.core.config import settings
from app.core.logging import configure_logging
from app.services.job_service import process_pending_jobs


def run_worker() -> None:
    configure_logging()
    while True:
        process_pending_jobs()
        time.sleep(settings.WORKER_POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run_worker()
