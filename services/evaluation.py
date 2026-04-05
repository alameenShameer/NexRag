from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .config import EVALUATION_STATUS_PATH, RAGAS_RESULTS_PATH, RAGAS_SUMMARY_PATH, ROOT_DIR


def _default_status() -> Dict[str, Any]:
    return {
        "state": "idle",
        "progress_percent": 0,
        "message": "Evaluation idle.",
        "started_at": None,
        "latest_summary": None,
        "last_error": None,
    }


class EvaluationService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        if not EVALUATION_STATUS_PATH.exists():
            self._write_status(_default_status())

    def _write_status(self, payload: Dict[str, Any]) -> None:
        with EVALUATION_STATUS_PATH.open("w", encoding="utf-8") as file_handle:
            json.dump(payload, file_handle, indent=2)

    def get_status(self) -> Dict[str, Any]:
        if not EVALUATION_STATUS_PATH.exists():
            status = _default_status()
            self._write_status(status)
            return status
        with EVALUATION_STATUS_PATH.open("r", encoding="utf-8") as file_handle:
            return json.load(file_handle)

    def latest_summary(self) -> Dict[str, Any]:
        if RAGAS_SUMMARY_PATH.exists():
            with RAGAS_SUMMARY_PATH.open("r", encoding="utf-8") as file_handle:
                return json.load(file_handle)
        return {
            "status": "not-run",
            "message": "RAGAS evaluation has not been run yet.",
            "metrics": {},
        }

    def refresh_summary_from_csv(self) -> Dict[str, Any]:
        if not RAGAS_RESULTS_PATH.exists():
            summary = self.latest_summary()
            self._write_summary(summary)
            return summary

        with RAGAS_RESULTS_PATH.open("r", encoding="utf-8") as file_handle:
            rows = list(csv.DictReader(file_handle))

        metrics: Dict[str, float] = {}
        if rows:
            last_row = rows[-1]
            for key, value in last_row.items():
                try:
                    metrics[key] = round(float(value), 4)
                except (TypeError, ValueError):
                    continue

        summary = {
            "status": "ready",
            "message": "Latest RAGAS evaluation summary loaded.",
            "metrics": metrics,
            "rows": len(rows),
            "source": str(RAGAS_RESULTS_PATH.name),
        }
        self._write_summary(summary)
        return summary

    def _write_summary(self, summary: Dict[str, Any]) -> None:
        with RAGAS_SUMMARY_PATH.open("w", encoding="utf-8") as file_handle:
            json.dump(summary, file_handle, indent=2)

    def run(self) -> Dict[str, Any]:
        with self._lock:
            current = self.get_status()
            if self._thread and self._thread.is_alive():
                return current

            def runner() -> None:
                command = [sys.executable, str(ROOT_DIR / "tools" / "evaluation" / "eval_ragas.py")]
                env = os.environ.copy()
                env["NEXRAG_EVALUATION_STATUS_PATH"] = str(EVALUATION_STATUS_PATH)
                completed = subprocess.run(command, cwd=ROOT_DIR, capture_output=True, text=True, env=env)
                summary = self.refresh_summary_from_csv()
                status = self.get_status()
                final_status = {
                    "state": "completed" if completed.returncode == 0 else "failed",
                    "progress_percent": 100 if completed.returncode == 0 else status.get("progress_percent", 0),
                    "message": "Evaluation completed." if completed.returncode == 0 else "Evaluation failed.",
                    "started_at": status.get("started_at"),
                    "latest_summary": summary,
                    "last_error": None if completed.returncode == 0 else "\n".join(completed.stderr.splitlines()[-20:]),
                    "stdout_tail": completed.stdout.splitlines()[-20:],
                    "stderr_tail": completed.stderr.splitlines()[-20:],
                }
                self._write_status(final_status)

            status = {
                "state": "running",
                "progress_percent": 1,
                "message": "Evaluation running...",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "latest_summary": self.latest_summary(),
                "last_error": None,
            }
            self._write_status(status)
            self._thread = threading.Thread(target=runner, daemon=True, name="nexrag-evaluation")
            self._thread.start()
            return self.get_status()


_evaluation_service = EvaluationService()


def get_evaluation_service() -> EvaluationService:
    return _evaluation_service
