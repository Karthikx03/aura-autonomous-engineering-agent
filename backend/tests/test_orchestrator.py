"""Unit tests for the Orchestrator's PLAN->ANALYZE->[IMPLEMENT->TEST->DEBUG]*->
SECURITY->VERIFY->COMMIT loop.

Stub agents below satisfy only the method signatures the Orchestrator
actually calls -- they do not subclass the real agent classes -- which
keeps these tests focused purely on the orchestration control flow.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.orchestrator.orchestrator import Orchestrator
from app.orchestrator.state import (
    CodeChange,
    DebugReport,
    PlanResult,
    RepoMap,
    SecurityReport,
    TestReport,
)
from app.websocket.events import AgentEvent


class StubPlanner:
    async def plan(self, goal: str, repo_map: RepoMap | None = None) -> PlanResult:
        return PlanResult(goal=goal, tasks=["do it"])


class StubRepoAnalyst:
    async def analyze(self, repo_path: str) -> RepoMap:
        return RepoMap(root=repo_path, languages=["python"], file_count=1)


class StubCoder:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def implement(self, plan: PlanResult, repo_path: str, debug_report: DebugReport | None = None):
        self.calls.append({"plan": plan, "repo_path": repo_path, "debug_report": debug_report})
        return [CodeChange(path="app.py", action="modified", diff_preview="...")]


class ScriptedTester:
    """Returns a scripted sequence of TestReports, one per call."""

    def __init__(self, reports: list[TestReport]) -> None:
        self.reports = reports
        self.call_count = 0

    async def run_tests(self, repo_path: str, test_command: str = "pytest -q") -> TestReport:
        report = self.reports[min(self.call_count, len(self.reports) - 1)]
        self.call_count += 1
        return report


class AlwaysFailingTester:
    def __init__(self) -> None:
        self.call_count = 0

    async def run_tests(self, repo_path: str, test_command: str = "pytest -q") -> TestReport:
        self.call_count += 1
        return TestReport(total=1, passed=0, failed=1, failures=["test_x failed"], raw_output="failed")


class StubDebugger:
    def __init__(self) -> None:
        self.call_count = 0

    async def debug(self, command: str, stdout: str, stderr: str, test_report: TestReport) -> DebugReport:
        self.call_count += 1
        return DebugReport(root_cause="bug", proposed_fix="fix it", confidence=0.5)


class StubSecurity:
    def __init__(self, blocking: bool = False) -> None:
        self.blocking = blocking
        self.call_count = 0

    async def scan(self, repo_path: str) -> SecurityReport:
        self.call_count += 1
        if self.blocking:
            from app.orchestrator.state import SecurityIssue

            return SecurityReport(issues=[SecurityIssue(rule_id="x", severity="critical", file="a.py", message="bad")])
        return SecurityReport(issues=[])


def make_orchestrator(
    tester,
    debugger=None,
    security=None,
    event_sink=None,
    git_committer=None,
):
    return Orchestrator(
        planner=StubPlanner(),
        repo_analyst=StubRepoAnalyst(),
        coder=StubCoder(),
        tester=tester,
        debugger=debugger or StubDebugger(),
        security=security or StubSecurity(),
        event_sink=event_sink,
        git_committer=git_committer,
    )


@pytest.mark.asyncio
async def test_fails_then_passes_on_second_iteration():
    reports = [
        TestReport(total=2, passed=1, failed=1, failures=["test_a failed"], raw_output="1 failed"),
        TestReport(total=2, passed=2, failed=0, raw_output="2 passed"),
    ]
    tester = ScriptedTester(reports)
    debugger = StubDebugger()

    orchestrator = make_orchestrator(tester, debugger=debugger)
    state = await orchestrator.run_task("Fix the bug", "/repo", max_iterations=5)

    assert state.succeeded
    assert state.status.value == "succeeded"
    assert len(state.history) == 2
    assert debugger.call_count == 1
    assert state.history[0].test_report.all_passed is False
    assert state.history[1].test_report.all_passed is True
    assert state.final_test_report.all_passed is True


@pytest.mark.asyncio
async def test_always_failing_stops_at_max_iterations():
    tester = AlwaysFailingTester()
    debugger = StubDebugger()

    orchestrator = make_orchestrator(tester, debugger=debugger)
    state = await orchestrator.run_task("Impossible task", "/repo", max_iterations=3)

    assert not state.succeeded
    assert state.status.value == "failed"
    assert state.error is not None
    assert len(state.history) == 3
    assert tester.call_count == 3
    # debugger runs after each non-final failed iteration only (iterations 1 and 2)
    assert debugger.call_count == 2


@pytest.mark.asyncio
async def test_git_committer_called_only_when_passed_and_not_blocking():
    reports = [TestReport(total=1, passed=1, failed=0, raw_output="passed")]
    tester = ScriptedTester(reports)

    commit_calls: list[tuple[str, str]] = []

    async def git_committer(repo_path: str, message: str) -> str:
        commit_calls.append((repo_path, message))
        return "abc123"

    orchestrator = make_orchestrator(tester, security=StubSecurity(blocking=False), git_committer=git_committer)
    state = await orchestrator.run_task("Simple fix", "/repo", max_iterations=3)

    assert state.succeeded
    assert commit_calls == [("/repo", "AURA: Simple fix")]
    assert state.commit_sha == "abc123"


@pytest.mark.asyncio
async def test_git_committer_not_called_when_security_blocking():
    reports = [TestReport(total=1, passed=1, failed=0, raw_output="passed")]
    tester = ScriptedTester(reports)

    commit_calls: list[tuple[str, str]] = []

    def git_committer(repo_path: str, message: str) -> str:
        commit_calls.append((repo_path, message))
        return "abc123"

    orchestrator = make_orchestrator(tester, security=StubSecurity(blocking=True), git_committer=git_committer)
    state = await orchestrator.run_task("Simple fix", "/repo", max_iterations=3)

    # Tests passed, but a blocking security issue must prevent commit.
    assert commit_calls == []
    assert state.commit_sha is None
    assert state.security_report.blocking is True


@pytest.mark.asyncio
async def test_git_committer_not_called_when_tests_never_pass():
    tester = AlwaysFailingTester()
    commit_calls: list[tuple[str, str]] = []

    def git_committer(repo_path: str, message: str) -> str:
        commit_calls.append((repo_path, message))
        return "abc123"

    orchestrator = make_orchestrator(tester, security=StubSecurity(blocking=False), git_committer=git_committer)
    state = await orchestrator.run_task("Impossible task", "/repo", max_iterations=2)

    assert not state.succeeded
    assert commit_calls == []
    assert state.commit_sha is None


@pytest.mark.asyncio
async def test_events_emitted_and_git_committer_optional():
    reports = [TestReport(total=1, passed=1, failed=0, raw_output="passed")]
    tester = ScriptedTester(reports)

    events: list[AgentEvent] = []

    async def sink(event: AgentEvent) -> None:
        events.append(event)

    orchestrator = make_orchestrator(tester, event_sink=sink, git_committer=None)
    state = await orchestrator.run_task("No git configured", "/repo", max_iterations=2)

    assert state.succeeded
    assert state.commit_sha is None  # no git_committer provided, must not fail the task
    event_types = [e.type.value for e in events]
    assert "task_started" in event_types
    assert "task_completed" in event_types
    assert "tests_passed" in event_types


@pytest.mark.asyncio
async def test_sync_event_sink_supported():
    reports = [TestReport(total=1, passed=1, failed=0, raw_output="passed")]
    tester = ScriptedTester(reports)

    events: list[AgentEvent] = []

    def sync_sink(event: AgentEvent) -> None:
        events.append(event)

    orchestrator = make_orchestrator(tester, event_sink=sync_sink)
    state = await orchestrator.run_task("Sync sink test", "/repo", max_iterations=1)

    assert state.succeeded
    assert len(events) > 0


@pytest.mark.asyncio
async def test_coder_receives_last_debug_report_on_retry():
    reports = [
        TestReport(total=1, passed=0, failed=1, failures=["boom"], raw_output="failed"),
        TestReport(total=1, passed=1, failed=0, raw_output="passed"),
    ]
    tester = ScriptedTester(reports)
    coder = StubCoder()

    orchestrator = Orchestrator(
        planner=StubPlanner(),
        repo_analyst=StubRepoAnalyst(),
        coder=coder,
        tester=tester,
        debugger=StubDebugger(),
        security=StubSecurity(),
    )
    await orchestrator.run_task("Retry goal", "/repo", max_iterations=3)

    assert len(coder.calls) == 2
    assert coder.calls[0]["debug_report"] is None
    assert coder.calls[1]["debug_report"] is not None
    assert coder.calls[1]["debug_report"].proposed_fix == "fix it"
