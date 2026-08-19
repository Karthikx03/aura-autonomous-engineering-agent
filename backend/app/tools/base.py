"""Tool abstraction.

Every capability an agent can invoke against a repository or the outside
world (reading/writing files, running commands, inspecting git, ...) is a
``Tool``. Tools are looked up by name through ``ToolRegistry`` rather than
imported directly by agents, which keeps agents testable with a fake
registry and keeps every invocation centrally logged.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.observability.logger import log_event


@dataclass
class ToolResult:
    status: str  # "success" | "error"
    output: Any = None
    error: str | None = None
    duration_seconds: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == "success"


class Tool(ABC):
    name: str = "tool"
    description: str = ""

    @abstractmethod
    async def _run(self, **kwargs: Any) -> Any:
        """Tool-specific implementation. Raise on failure."""

    async def run(self, *, agent: str = "unknown", **kwargs: Any) -> ToolResult:
        started = time.perf_counter()
        try:
            output = await self._run(**kwargs)
            result = ToolResult(status="success", output=output, duration_seconds=time.perf_counter() - started)
        except Exception as exc:
            result = ToolResult(status="error", error=str(exc), duration_seconds=time.perf_counter() - started)
        log_event(
            {
                "event": "tool_call",
                "agent": agent,
                "tool": self.name,
                "file": kwargs.get("path") or kwargs.get("file") or kwargs.get("file_path"),
                "status": result.status,
                "duration_seconds": result.duration_seconds,
            }
        )
        return result


@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self.tools:
            raise KeyError(f"Unknown tool '{name}'. Registered: {sorted(self.tools)}")
        return self.tools[name]

    def names(self) -> list[str]:
        return sorted(self.tools)

    async def call(self, name: str, *, agent: str = "unknown", **kwargs: Any) -> ToolResult:
        return await self.get(name).run(agent=agent, **kwargs)
