"""Structured logging + lightweight in-memory metrics for AURA.

Every tool call and agent event is logged as a single-line JSON object so
logs are trivially machine-parseable (and easy to ship to a real log
aggregator later). Metrics are exposed both as simple in-memory counters
(read by the /metrics dashboard endpoint) and, when the ``prometheus_client``
package is available, as real Prometheus metrics.
"""
from __future__ import annotations

import json
import logging
import sys
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

_LOGGER_NAME = "aura"


def _build_logger() -> logging.Logger:
    logger = logging.getLogger(_LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


_logger = _build_logger()


def log_event(event: dict[str, Any]) -> dict[str, Any]:
    """Emit a structured JSON log line and return the enriched event."""
    enriched = {"timestamp": time.time(), **event}
    _logger.info(json.dumps(enriched, default=str))
    METRICS.record_event(enriched)
    return enriched


@dataclass
class InMemoryMetrics:
    """Process-local metrics store.

    This is intentionally simple (no external dependency required to run
    the test suite or a quick demo) but is structured so it can be backed
    by Prometheus counters/histograms in production — see ``prometheus.py``.
    """

    tool_calls_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    tool_call_errors_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    agent_events_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    task_durations_seconds: list[float] = field(default_factory=list)
    llm_calls_total: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    llm_latency_seconds: list[float] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record_event(self, event: dict[str, Any]) -> None:
        with self._lock:
            kind = event.get("event")
            if kind == "tool_call":
                self.tool_calls_total[event.get("tool", "unknown")] += 1
                if event.get("status") == "error":
                    self.tool_call_errors_total[event.get("tool", "unknown")] += 1
            elif kind == "agent_event":
                self.agent_events_total[event.get("agent", "unknown")] += 1
            elif kind == "task_completed" and "duration_seconds" in event:
                self.task_durations_seconds.append(float(event["duration_seconds"]))
            elif kind == "llm_call":
                self.llm_calls_total[event.get("provider", "unknown")] += 1
                if "latency_seconds" in event:
                    self.llm_latency_seconds.append(float(event["latency_seconds"]))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            avg_duration = (
                sum(self.task_durations_seconds) / len(self.task_durations_seconds)
                if self.task_durations_seconds
                else 0.0
            )
            avg_llm_latency = (
                sum(self.llm_latency_seconds) / len(self.llm_latency_seconds)
                if self.llm_latency_seconds
                else 0.0
            )
            return {
                "tool_calls_total": dict(self.tool_calls_total),
                "tool_call_errors_total": dict(self.tool_call_errors_total),
                "agent_events_total": dict(self.agent_events_total),
                "llm_calls_total": dict(self.llm_calls_total),
                "tasks_completed": len(self.task_durations_seconds),
                "avg_task_duration_seconds": round(avg_duration, 3),
                "avg_llm_latency_seconds": round(avg_llm_latency, 3),
            }


METRICS = InMemoryMetrics()


def get_logger() -> logging.Logger:
    return _logger
