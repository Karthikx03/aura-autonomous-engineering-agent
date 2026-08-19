"""Deterministic offline provider.

Used as the default provider so AURA's tests, CI pipeline, and demo mode
run correctly with zero API keys and no network access. It returns
canned-but-structurally-valid responses (including valid JSON when
``json_mode=True``) based on simple keyword matching against the last user
message, which is enough for the agents' own JSON-schema parsing to be
exercised for real.
"""
from __future__ import annotations

import json

from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage


class MockProvider(LLMProvider):
    name = "mock"

    def __init__(self, model: str = "aura-mock-1") -> None:
        self.model = model

    def is_configured(self) -> bool:
        return True

    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        content = self._respond(last_user, json_mode=json_mode)
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        return LLMResponse(
            content=content,
            model=self.model,
            provider=self.name,
            usage=LLMUsage(prompt_tokens=prompt_tokens, completion_tokens=len(content.split())),
            raw={"mock": True},
        )

    def _respond(self, prompt: str, *, json_mode: bool) -> str:
        lowered = prompt.lower()
        if json_mode:
            return json.dumps(self._json_payload(lowered))
        if "plan" in lowered:
            return "Plan: break the goal into discrete, testable implementation steps."
        if "debug" in lowered or "failure" in lowered:
            return "The failure stems from a mismatch between expected and actual output; a targeted fix is proposed."
        return f"Acknowledged request ({len(prompt)} chars). Proceeding with the requested engineering task."

    def _json_payload(self, lowered: str) -> dict:
        if "plan" in lowered:
            return {
                "goal": "Implement the requested change",
                "requirements": ["Understand existing code", "Implement change", "Add tests"],
                "tasks": ["Analyze repository", "Modify source files", "Write/adjust tests"],
                "files": [],
                "tests": ["Run existing test suite", "Add regression test"],
                "risks": ["Possible regression in dependent modules"],
            }
        if "debug" in lowered or "failure" in lowered:
            return {
                "root_cause": "Assertion mismatch between expected and actual value",
                "affected_files": [],
                "proposed_fix": "Align implementation output with the test's expected contract",
                "confidence": 0.72,
            }
        if "security" in lowered:
            return {"issues": []}
        if "repo" in lowered or "analy" in lowered:
            return {
                "languages": ["python"],
                "frameworks": [],
                "has_tests": True,
                "summary": "Repository analyzed successfully.",
            }
        return {"result": "ok"}
