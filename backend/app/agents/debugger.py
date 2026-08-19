"""DebuggerAgent: analyzes a test failure and proposes a fix."""
from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.llm.base import LLMMessage
from app.orchestrator.state import DebugReport, TestReport

_SYSTEM_PROMPT = (
    "You are the debugging agent of AURA. Given a command, its stdout/stderr, "
    "and a test failure report, diagnose the root cause and propose a fix. "
    "Respond with a single JSON object: {\"root_cause\": \"...\", "
    '"affected_files": [...], "proposed_fix": "...", "confidence": 0.0-1.0}. '
    "Respond with JSON only."
)


class DebuggerAgent(BaseAgent):
    name = "debugger"

    async def debug(
        self,
        command: str,
        stdout: str,
        stderr: str,
        test_report: TestReport,
    ) -> DebugReport:
        self.emit("Debugging started", command=command, failed=test_report.failed)

        prompt = (
            "Analyze this test failure and propose a fix.\n"
            f"Command: {command}\n"
            f"Failures: {test_report.failures}\n"
            f"Stdout:\n{stdout}\n"
            f"Stderr:\n{stderr}\n"
        )
        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        response = await self.llm.complete(messages, json_mode=True)
        report = self._parse(response.content, test_report)

        self.emit("Debugging completed", confidence=report.confidence)
        return report

    def _parse(self, content: str, test_report: TestReport) -> DebugReport:
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("debug JSON is not an object")
            defaults = {
                "root_cause": "Unknown root cause",
                "proposed_fix": "Re-examine failing tests and adjust implementation.",
            }
            merged = {**defaults, **parsed}
            return DebugReport.model_validate(merged)
        except Exception as exc:
            self.emit("Debug JSON parse failed, using fallback report", error=str(exc))
            return DebugReport(
                root_cause="Could not parse LLM diagnosis; failures observed in test run.",
                affected_files=[],
                proposed_fix="Inspect failing tests manually: " + "; ".join(test_report.failures[:5]),
                confidence=0.0,
            )
