import logging
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class IndustryLogger:
    """
    Structured logger that simulates industry practices.
    - Logs to both console and a daily log file (JSON format)
    - Supports trace recording: capture full agent runs and save to traces/
    """

    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # File Handler (daily log)
        log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")

        # Console Handler
        console_handler = logging.StreamHandler()

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # ── Trace recording state ──
        self._trace_active: bool = False
        self._trace_steps: List[Dict[str, Any]] = []
        self._trace_meta: Dict[str, Any] = {}

    # ─────────────────────────────────────────
    # Core logging
    # ─────────────────────────────────────────

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Logs a structured event with timestamp."""
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event_type,
            "data": data,
        }
        self.logger.info(json.dumps(payload, ensure_ascii=False))

        # If a trace is active, also record the event
        if self._trace_active:
            self._trace_steps.append(payload)

    def info(self, msg: str):
        self.logger.info(msg)

    def error(self, msg: str, exc_info: bool = True):
        self.logger.error(msg, exc_info=exc_info)

    # ─────────────────────────────────────────
    # Trace recording (for submission)
    # ─────────────────────────────────────────

    def start_trace(self, agent_version: str, query: str):
        """
        Start recording a trace session.
        Call this at the beginning of an agent run.
        """
        self._trace_active = True
        self._trace_steps = []
        self._trace_meta = {
            "agent_version": agent_version,
            "query": query,
            "started_at": datetime.utcnow().isoformat(),
        }

    def save_trace(self, outcome: str, trace_name: Optional[str] = None):
        """
        Stop recording and save trace to traces/success/ or traces/failure/.

        Args:
            outcome: 'success' or 'failure'
            trace_name: optional custom filename (without .json)
        """
        if not self._trace_active:
            self.info("No active trace to save.")
            return

        self._trace_active = False
        self._trace_meta["ended_at"] = datetime.utcnow().isoformat()
        self._trace_meta["outcome"] = outcome
        self._trace_meta["total_steps"] = len(self._trace_steps)

        trace_doc = {
            "meta": self._trace_meta,
            "steps": self._trace_steps,
        }

        # Build output path
        out_dir = os.path.join("traces", outcome)
        os.makedirs(out_dir, exist_ok=True)

        if not trace_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            agent_ver = self._trace_meta.get("agent_version", "agent")
            trace_name = f"trace_{agent_ver}_{outcome}_{ts}"

        out_path = os.path.join(out_dir, f"{trace_name}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(trace_doc, f, indent=2, ensure_ascii=False)

        self.info(f"[TraceLogger] Trace saved → {out_path}")
        return out_path


# Global logger instance
logger = IndustryLogger()
