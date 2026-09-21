"""
Lightweight background scheduler for the session-cleanup job (production-
roadmap item: "Add session cleanup jobs"). Uses stdlib `threading` only —
no APScheduler dependency. Good enough for a single-process deployment;
for multi-instance deployments, run `flask cleanup-sessions` from an
external cron/k8s CronJob instead (see README) so the job isn't
duplicated per instance.
"""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger("app.scheduler")


class SessionCleanupScheduler:
    def __init__(self, app, interval_minutes: int):
        self.app = app
        self.interval_seconds = max(interval_minutes, 1) * 60
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self):
        # Avoid a burst of cleanup work at the exact moment of boot.
        self._stop_event.wait(self.interval_seconds)
        while not self._stop_event.is_set():
            try:
                with self.app.app_context():
                    from services.auth_service import AuthService
                    AuthService().cleanup_expired_sessions()
            except Exception:
                logger.exception("session_cleanup_job_failed")
            self._stop_event.wait(self.interval_seconds)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, name="session-cleanup", daemon=True)
        self._thread.start()
        logger.info("session_cleanup_scheduler_started", extra={"interval_seconds": self.interval_seconds})

    def stop(self):
        self._stop_event.set()
