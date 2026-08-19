"""TestingAgent: runs the repository test suite via the run_tests tool."""
from __future__ import annotations

from app.agents.base import BaseAgent
from app.orchestrator.state import TestReport


class TestingAgent(BaseAgent):
    name = "tester"

    async def run_tests(self, repo_path: str, test_command: str = "pytest -q") -> TestReport:
        self.emit("Test run started", repo_path=repo_path, test_command=test_command)

        if self.tools is None:
            report = TestReport(total=0, raw_output="No tool registry available to run tests.")
            self.emit("Test run skipped: no tool registry")
            return report

        result = await self.tools.call(
            "run_tests", cwd=repo_path, test_command=test_command, agent=self.name
        )

        if result.ok and isinstance(result.output, dict):
            report = TestReport(**result.output)
        else:
            report = TestReport(total=0, raw_output=result.error or "run_tests tool failed")

        self.emit(
            "Test run completed",
            total=report.total,
            passed=report.passed,
            failed=report.failed,
            all_passed=report.all_passed,
        )
        return report
