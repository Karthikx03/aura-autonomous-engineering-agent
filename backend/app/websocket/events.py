"""Event schema broadcast to the UI over WebSockets.

Agents never stream raw chain-of-thought (see project spec §15) — only
concise, structured summaries of what they analyzed, did, and found.
"""
from __future__ import annotations

import time
from enum import Enum

from pydantic import BaseModel, Field


class EventType(str, Enum):
    TASK_STARTED = "task_started"
    PLANNER_STARTED = "planner_started"
    PLANNER_COMPLETED = "planner_completed"
    REPO_ANALYSIS_STARTED = "repo_analysis_started"
    REPO_ANALYSIS_COMPLETED = "repo_analysis_completed"
    CODER_STARTED = "coder_started"
    FILE_MODIFIED = "file_modified"
    CODER_COMPLETED = "coder_completed"
    COMMAND_EXECUTED = "command_executed"
    TESTS_STARTED = "tests_started"
    TESTS_PASSED = "tests_passed"
    TESTS_FAILED = "tests_failed"
    DEBUGGER_STARTED = "debugger_started"
    DEBUGGER_COMPLETED = "debugger_completed"
    FIX_APPLIED = "fix_applied"
    SECURITY_SCAN_STARTED = "security_scan_started"
    SECURITY_SCAN_COMPLETED = "security_scan_completed"
    GIT_DIFF_READY = "git_diff_ready"
    GIT_COMMIT_CREATED = "git_commit_created"
    ITERATION_COMPLETED = "iteration_completed"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"


class AgentEvent(BaseModel):
    type: EventType
    agent: str
    message: str
    task_id: str | None = None
    data: dict = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
