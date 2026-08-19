"""Shared state models for a single autonomous task run."""
from __future__ import annotations

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    ANALYZING = "analyzing"
    IMPLEMENTING = "implementing"
    TESTING = "testing"
    DEBUGGING = "debugging"
    SECURITY_CHECK = "security_check"
    VERIFYING = "verifying"
    COMMITTING = "committing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PlanResult(BaseModel):
    goal: str
    requirements: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    tests: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class RepoMap(BaseModel):
    root: str
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    test_files: list[str] = Field(default_factory=list)
    has_git: bool = False
    file_count: int = 0
    summary: str = ""


class CodeChange(BaseModel):
    path: str
    action: str  # "created" | "modified" | "deleted"
    diff_preview: str = ""


class TestReport(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    coverage_percent: float | None = None
    duration_seconds: float = 0.0
    failures: list[str] = Field(default_factory=list)
    raw_output: str = ""

    @property
    def all_passed(self) -> bool:
        return self.total > 0 and self.failed == 0


class DebugReport(BaseModel):
    root_cause: str
    affected_files: list[str] = Field(default_factory=list)
    proposed_fix: str
    confidence: float = 0.0


class SecurityIssue(BaseModel):
    rule_id: str
    severity: str  # "low" | "medium" | "high" | "critical"
    file: str
    line: int | None = None
    message: str


class SecurityReport(BaseModel):
    issues: list[SecurityIssue] = Field(default_factory=list)

    @property
    def blocking(self) -> bool:
        return any(i.severity in ("high", "critical") for i in self.issues)


class IterationRecord(BaseModel):
    iteration: int
    summary: str
    test_report: TestReport | None = None
    debug_report: DebugReport | None = None
    changes: list[CodeChange] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class TaskState(BaseModel):
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str
    repo_path: str
    status: TaskStatus = TaskStatus.PENDING
    max_iterations: int = 5
    iteration: int = 0
    plan: PlanResult | None = None
    repo_map: RepoMap | None = None
    history: list[IterationRecord] = Field(default_factory=list)
    security_report: SecurityReport | None = None
    final_test_report: TestReport | None = None
    commit_sha: str | None = None
    started_at: float = Field(default_factory=time.time)
    finished_at: float | None = None
    error: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status == TaskStatus.SUCCEEDED
