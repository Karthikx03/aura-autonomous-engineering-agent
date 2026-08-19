"""PlannerAgent: turns a natural-language goal into a structured PlanResult."""
from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.llm.base import LLMMessage
from app.orchestrator.state import PlanResult, RepoMap

_SYSTEM_PROMPT = (
    "You are the planning agent of AURA, an autonomous software engineering "
    "system. Given a goal, produce a plan as a single JSON object with keys: "
    'goal (string), requirements (list of strings), tasks (list of strings), '
    "files (list of file paths likely to be touched), tests (list of test "
    "descriptions), risks (list of strings). Respond with JSON only."
)


class PlannerAgent(BaseAgent):
    name = "planner"

    async def plan(self, goal: str, repo_map: RepoMap | None = None) -> PlanResult:
        self.emit("Planning started", goal=goal)

        prompt_lines = ["Create an implementation plan for the following goal:", goal]
        if repo_map is not None:
            prompt_lines.append(
                "Repository context: "
                f"languages={repo_map.languages}, frameworks={repo_map.frameworks}, "
                f"file_count={repo_map.file_count}, summary={repo_map.summary!r}"
            )
        prompt_lines.append(
            "Return a JSON plan object with keys goal, requirements, tasks, files, tests, risks."
        )
        prompt = "\n".join(prompt_lines)

        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        response = await self.llm.complete(messages, json_mode=True)

        plan = self._parse(response.content, goal)
        self.emit("Planning completed", tasks=len(plan.tasks), files=len(plan.files))
        return plan

    def _parse(self, content: str, goal: str) -> PlanResult:
        try:
            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                raise ValueError("plan JSON is not an object")
            defaults = {"goal": goal}
            merged = {**defaults, **parsed}
            return PlanResult.model_validate(merged)
        except Exception as exc:
            self.emit("Planning JSON parse failed, using fallback plan", error=str(exc))
            return PlanResult(
                goal=goal,
                requirements=[],
                tasks=[goal],
                files=[],
                tests=[],
                risks=["Plan could not be parsed from the LLM response; proceeding with a minimal plan."],
            )
