"""Orchestrator: drives a single autonomous engineering task end to end.

Loop: PLAN -> ANALYZE -> [IMPLEMENT -> TEST -> (DEBUG)]* -> SECURITY -> VERIFY
-> COMMIT. The iteration loop is hard-bounded by ``max_iterations`` -- there
is no infinite retry. Security and reporting always run, even if the task
never got tests to pass, so callers always get a complete ``TaskState``.
"""
from __future__ import annotations

import inspect
import time
from typing import Awaitable, Callable

from app.agents.coder import CoderAgent
from app.agents.debugger import DebuggerAgent
from app.agents.planner import PlannerAgent
from app.agents.repo_analyst import RepoAnalystAgent
from app.agents.security import SecurityAgent
from app.agents.tester import TestingAgent
from app.observability.logger import log_event
from app.orchestrator.state import DebugReport, IterationRecord, TaskState, TaskStatus
from app.websocket.events import AgentEvent, EventType

EventSink = Callable[[AgentEvent], "Awaitable[None] | None"]
GitCommitter = Callable[[str, str], "Awaitable[str] | str"]


class Orchestrator:
    def __init__(
        self,
        planner: PlannerAgent,
        repo_analyst: RepoAnalystAgent,
        coder: CoderAgent,
        tester: TestingAgent,
        debugger: DebuggerAgent,
        security: SecurityAgent,
        event_sink: EventSink | None = None,
        git_committer: GitCommitter | None = None,
    ) -> None:
        self.planner = planner
        self.repo_analyst = repo_analyst
        self.coder = coder
        self.tester = tester
        self.debugger = debugger
        self.security = security
        self.event_sink = event_sink
        self.git_committer = git_committer

    async def _emit(self, state: TaskState, event_type: EventType, message: str, **data) -> None:
        if self.event_sink is None:
            return
        event = AgentEvent(type=event_type, agent="orchestrator", message=message, task_id=state.task_id, data=data)
        result = self.event_sink(event)
        if inspect.isawaitable(result):
            await result

    async def run_task(self, goal: str, repo_path: str, max_iterations: int | None = None) -> TaskState:
        state = TaskState(
            goal=goal,
            repo_path=repo_path,
            max_iterations=max_iterations or 5,
        )

        await self._emit(state, EventType.TASK_STARTED, f"Starting task: {goal}")

        # --- PLAN ---
        state.status = TaskStatus.PLANNING
        await self._emit(state, EventType.PLANNER_STARTED, "Planning started")
        state.plan = await self.planner.plan(goal)
        await self._emit(state, EventType.PLANNER_COMPLETED, "Planning completed", tasks=len(state.plan.tasks))

        # --- ANALYZE ---
        state.status = TaskStatus.ANALYZING
        await self._emit(state, EventType.REPO_ANALYSIS_STARTED, "Repository analysis started")
        state.repo_map = await self.repo_analyst.analyze(repo_path)
        await self._emit(
            state, EventType.REPO_ANALYSIS_COMPLETED, "Repository analysis completed",
            languages=state.repo_map.languages,
        )

        last_debug_report: DebugReport | None = None
        last_test_report = None
        succeeded = False

        for iteration in range(1, state.max_iterations + 1):
            state.iteration = iteration
            is_last_iteration = iteration == state.max_iterations

            # --- IMPLEMENT ---
            state.status = TaskStatus.IMPLEMENTING
            await self._emit(state, EventType.CODER_STARTED, "Implementation started", iteration=iteration)
            changes = await self.coder.implement(state.plan, repo_path, debug_report=last_debug_report)
            await self._emit(state, EventType.CODER_COMPLETED, "Implementation completed", changes=len(changes))

            # --- TEST ---
            state.status = TaskStatus.TESTING
            await self._emit(state, EventType.TESTS_STARTED, "Test run started", iteration=iteration)
            test_report = await self.tester.run_tests(repo_path)
            last_test_report = test_report

            if test_report.all_passed:
                await self._emit(state, EventType.TESTS_PASSED, "Tests passed", iteration=iteration)
            else:
                await self._emit(
                    state, EventType.TESTS_FAILED, "Tests failed", iteration=iteration, failed=test_report.failed
                )

            debug_report: DebugReport | None = None
            if not test_report.all_passed and not is_last_iteration:
                state.status = TaskStatus.DEBUGGING
                await self._emit(state, EventType.DEBUGGER_STARTED, "Debugging started", iteration=iteration)
                debug_report = await self.debugger.debug(
                    command="pytest -q",
                    stdout=test_report.raw_output,
                    stderr="",
                    test_report=test_report,
                )
                await self._emit(
                    state,
                    EventType.DEBUGGER_COMPLETED,
                    "Debugging completed",
                    confidence=debug_report.confidence,
                )

            record = IterationRecord(
                iteration=iteration,
                summary=f"Iteration {iteration}: {len(changes)} change(s), "
                f"{'tests passed' if test_report.all_passed else 'tests failed'}.",
                test_report=test_report,
                debug_report=debug_report,
                changes=changes,
            )
            state.history.append(record)
            await self._emit(state, EventType.ITERATION_COMPLETED, record.summary, iteration=iteration)

            if test_report.all_passed:
                succeeded = True
                break

            last_debug_report = debug_report

        if not succeeded:
            state.status = TaskStatus.FAILED
            state.error = (
                f"Task did not pass tests within {state.max_iterations} iteration(s)."
            )

        # --- SECURITY (always runs) ---
        state.status = TaskStatus.SECURITY_CHECK
        await self._emit(state, EventType.SECURITY_SCAN_STARTED, "Security scan started")
        state.security_report = await self.security.scan(repo_path)
        await self._emit(
            state, EventType.SECURITY_SCAN_COMPLETED, "Security scan completed",
            issues=len(state.security_report.issues), blocking=state.security_report.blocking,
        )

        # --- VERIFY ---
        state.status = TaskStatus.VERIFYING
        state.final_test_report = last_test_report

        # --- COMMIT ---
        can_commit = succeeded and not state.security_report.blocking
        if can_commit:
            state.status = TaskStatus.COMMITTING
            if self.git_committer is None:
                log_event(
                    {
                        "event": "agent_event",
                        "agent": "orchestrator",
                        "message": "Git commit skipped: no git_committer configured",
                        "task_id": state.task_id,
                    }
                )
            else:
                commit_message = f"AURA: {goal}"
                result = self.git_committer(repo_path, commit_message)
                if inspect.isawaitable(result):
                    result = await result
                state.commit_sha = result
                await self._emit(
                    state, EventType.GIT_COMMIT_CREATED, "Git commit created", commit_sha=state.commit_sha
                )
        elif state.security_report.blocking:
            log_event(
                {
                    "event": "agent_event",
                    "agent": "orchestrator",
                    "message": "Commit skipped: security scan found blocking issues",
                    "task_id": state.task_id,
                }
            )

        state.status = TaskStatus.SUCCEEDED if succeeded else TaskStatus.FAILED
        state.finished_at = time.time()

        if succeeded:
            await self._emit(state, EventType.TASK_COMPLETED, "Task completed successfully")
        else:
            await self._emit(state, EventType.TASK_FAILED, state.error or "Task failed")

        return state
