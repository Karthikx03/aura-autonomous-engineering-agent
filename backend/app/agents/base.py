"""Base class shared by every specialized agent."""
from __future__ import annotations

from app.llm.base import LLMProvider
from app.observability.logger import log_event
from app.tools.base import ToolRegistry


class BaseAgent:
    name: str = "agent"

    def __init__(self, llm: LLMProvider, tools: ToolRegistry | None = None) -> None:
        self.llm = llm
        self.tools = tools

    def emit(self, message: str, **data) -> None:
        log_event({"event": "agent_event", "agent": self.name, "message": message, **data})
