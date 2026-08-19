"""Unit tests for backend/app/agents/*.

Each agent is exercised against MockProvider (or a locally-defined stub
LLMProvider when a specific realistic JSON payload is needed) and a small
in-memory fake ToolRegistry/Tool implementation that records every call it
receives, so we can assert both parsing/fallback behavior and that tools
are actually invoked with the expected arguments.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.agents.coder import CoderAgent
from app.agents.debugger import DebuggerAgent
from app.agents.planner import PlannerAgent
from app.agents.repo_analyst import RepoAnalystAgent
from app.agents.security import SecurityAgent
from app.agents.tester import TestingAgent
from app.llm.base import LLMMessage, LLMProvider, LLMResponse, LLMUsage
from app.llm.mock_provider import MockProvider
from app.orchestrator.state import DebugReport, PlanResult, RepoMap, TestReport
from app.tools.base import Tool, ToolRegistry


# --------------------------------------------------------------------------
# Local test doubles
# --------------------------------------------------------------------------


class StubLLMProvider(LLMProvider):
    """Returns a fixed literal response regardless of the prompt."""

    name = "stub"

    def __init__(self, content: str, model: str = "stub-1") -> None:
        self._content = content
        self.model = model
        self.calls: list[list[LLMMessage]] = []

    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        self.calls.append(messages)
        return LLMResponse(content=self._content, model=self.model, provider=self.name, usage=LLMUsage())


class BrokenJSONProvider(LLMProvider):
    """Always returns invalid JSON, to exercise fallback parsing paths."""

    name = "broken"

    async def _complete(
        self,
        messages: list[LLMMessage],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        return LLMResponse(content="not valid json {{{", model="broken-1", provider=self.name, usage=LLMUsage())


class FakeReadFileTool(Tool):
    name = "read_file"

    def __init__(self, files: dict[str, str]) -> None:
        self.files = files
        self.calls: list[dict] = []

    async def _run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        path = kwargs["path"]
        if path not in self.files:
            raise FileNotFoundError(path)
        return self.files[path]


class FakeWriteFileTool(Tool):
    name = "write_file"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[dict] = []

    async def _run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        path = self.root / kwargs["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        content = kwargs["content"]
        path.write_text(content)
        return {"path": kwargs["path"], "bytes_written": len(content.encode())}


class FakeEditFileTool(Tool):
    name = "edit_file"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[dict] = []

    async def _run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        path = self.root / kwargs["path"]
        text = path.read_text()
        find = kwargs["find"]
        replace = kwargs["replace"]
        count = text.count(find)
        path.write_text(text.replace(find, replace))
        return {"path": kwargs["path"], "replacements": count}


class FakeListDirectoryTool(Tool):
    name = "list_directory"

    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[dict] = []

    async def _run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file())


class FakeRunTestsTool(Tool):
    name = "run_tests"

    def __init__(self, output: dict | None = None, raise_error: str | None = None) -> None:
        self.output = output
        self.raise_error = raise_error
        self.calls: list[dict] = []

    async def _run(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if self.raise_error:
            raise RuntimeError(self.raise_error)
        return self.output


def make_registry(*tools: Tool) -> ToolRegistry:
    registry = ToolRegistry()
    for tool in tools:
        registry.register(tool)
    return registry


# --------------------------------------------------------------------------
# PlannerAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_planner_parses_mock_provider_plan():
    agent = PlannerAgent(llm=MockProvider())
    plan = await agent.plan("Add a health check endpoint")

    assert isinstance(plan, PlanResult)
    assert plan.tasks
    assert plan.requirements
    assert "Run existing test suite" in plan.tests


@pytest.mark.asyncio
async def test_planner_falls_back_on_broken_json():
    agent = PlannerAgent(llm=BrokenJSONProvider())
    plan = await agent.plan("Do something")

    assert isinstance(plan, PlanResult)
    assert plan.goal == "Do something"
    assert plan.tasks == ["Do something"]
    assert plan.risks  # fallback notes the parse failure


@pytest.mark.asyncio
async def test_planner_includes_repo_map_context_in_prompt():
    provider = StubLLMProvider(
        content=json.dumps(
            {
                "goal": "Add tests",
                "requirements": ["r1"],
                "tasks": ["t1"],
                "files": ["a.py"],
                "tests": ["test_a"],
                "risks": [],
            }
        )
    )
    agent = PlannerAgent(llm=provider)
    repo_map = RepoMap(root=".", languages=["python"], frameworks=["fastapi"], file_count=10)

    plan = await agent.plan("Add tests", repo_map=repo_map)

    assert plan.files == ["a.py"]
    sent_prompt = provider.calls[0][-1].content
    assert "fastapi" in sent_prompt
    assert "python" in sent_prompt


# --------------------------------------------------------------------------
# RepoAnalystAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repo_analyst_detects_structure(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("fastapi==0.100\npytest\n")
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("print('hi')\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text("def test_x(): assert True\n")
    (tmp_path / ".git").mkdir()

    agent = RepoAnalystAgent(llm=MockProvider())
    repo_map = await agent.analyze(str(tmp_path))

    assert "python" in repo_map.languages
    assert "fastapi" in repo_map.frameworks
    assert "pytest" in repo_map.frameworks
    assert repo_map.has_git is True
    assert any("test_main.py" in f for f in repo_map.test_files)
    assert repo_map.file_count >= 3
    assert repo_map.summary  # populated, either from LLM or fallback


@pytest.mark.asyncio
async def test_repo_analyst_skips_ignored_directories(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "junk.js").write_text("var x = 1;")
    (tmp_path / "src.py").write_text("x = 1\n")

    agent = RepoAnalystAgent(llm=MockProvider())
    repo_map = await agent.analyze(str(tmp_path))

    assert repo_map.file_count == 1
    assert repo_map.languages == ["python"]


# --------------------------------------------------------------------------
# CoderAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_coder_applies_write_edit_from_stub_llm(tmp_path: Path):
    edit_payload = {
        "edits": [
            {"path": "app/new_module.py", "action": "create", "content_or_patch": "def foo():\n    return 42\n"}
        ]
    }
    provider = StubLLMProvider(content=json.dumps(edit_payload))
    write_tool = FakeWriteFileTool(tmp_path)
    registry = make_registry(write_tool, FakeEditFileTool(tmp_path), FakeReadFileTool({}), FakeListDirectoryTool(tmp_path))

    agent = CoderAgent(llm=provider, tools=registry)
    plan = PlanResult(goal="Add foo()", files=["app/new_module.py"])

    changes = await agent.implement(plan, str(tmp_path))

    assert len(changes) == 1
    assert changes[0].path == "app/new_module.py"
    assert changes[0].action == "created"
    assert (tmp_path / "app" / "new_module.py").read_text() == "def foo():\n    return 42\n"
    assert write_tool.calls[0]["path"] == "app/new_module.py"


@pytest.mark.asyncio
async def test_coder_applies_find_replace_patch(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("VALUE = 1\n")

    edit_payload = {
        "edits": [
            {
                "path": "app.py",
                "action": "modify",
                "content_or_patch": {"find": "VALUE = 1", "replace": "VALUE = 2"},
            }
        ]
    }
    provider = StubLLMProvider(content=json.dumps(edit_payload))
    edit_tool = FakeEditFileTool(tmp_path)
    registry = make_registry(FakeWriteFileTool(tmp_path), edit_tool, FakeReadFileTool({}))

    agent = CoderAgent(llm=provider, tools=registry)
    plan = PlanResult(goal="Bump VALUE", files=["app.py"])

    changes = await agent.implement(plan, str(tmp_path))

    assert target.read_text() == "VALUE = 2\n"
    assert changes[0].action == "modified"
    assert edit_tool.calls[0]["find"] == "VALUE = 1"


@pytest.mark.asyncio
async def test_coder_incorporates_debug_report_in_followup_pass(tmp_path: Path):
    provider = StubLLMProvider(
        content=json.dumps(
            {"edits": [{"path": "fix.py", "action": "create", "content_or_patch": "# fixed\n"}]}
        )
    )
    registry = make_registry(FakeWriteFileTool(tmp_path), FakeEditFileTool(tmp_path), FakeReadFileTool({}))
    agent = CoderAgent(llm=provider, tools=registry)
    plan = PlanResult(goal="Fix bug")
    debug_report = DebugReport(root_cause="off by one", proposed_fix="adjust index", confidence=0.9)

    changes = await agent.implement(plan, str(tmp_path), debug_report=debug_report)

    assert len(changes) == 1
    sent_prompt = provider.calls[0][-1].content
    assert "off by one" in sent_prompt
    assert "adjust index" in sent_prompt


@pytest.mark.asyncio
async def test_coder_no_edits_on_broken_json(tmp_path: Path):
    registry = make_registry(FakeWriteFileTool(tmp_path), FakeEditFileTool(tmp_path))
    agent = CoderAgent(llm=BrokenJSONProvider(), tools=registry)
    plan = PlanResult(goal="Do nothing parsable")

    changes = await agent.implement(plan, str(tmp_path))

    assert changes == []


# --------------------------------------------------------------------------
# DebuggerAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_debugger_parses_mock_provider_report():
    agent = DebuggerAgent(llm=MockProvider())
    test_report = TestReport(total=3, passed=2, failed=1, failures=["test_x failed"])

    report = await agent.debug(
        command="pytest -q", stdout="", stderr="AssertionError", test_report=test_report
    )

    assert isinstance(report, DebugReport)
    assert report.confidence == 0.72
    assert report.proposed_fix


@pytest.mark.asyncio
async def test_debugger_falls_back_on_broken_json():
    agent = DebuggerAgent(llm=BrokenJSONProvider())
    test_report = TestReport(total=1, passed=0, failed=1, failures=["test_y failed"])

    report = await agent.debug(command="pytest -q", stdout="", stderr="", test_report=test_report)

    assert "test_y failed" in report.proposed_fix
    assert report.confidence == 0.0


# --------------------------------------------------------------------------
# TestingAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tester_maps_tool_output_to_test_report():
    output = {
        "total": 5,
        "passed": 5,
        "failed": 0,
        "skipped": 0,
        "coverage_percent": 91.5,
        "duration_seconds": 1.2,
        "raw_output": "5 passed",
        "failures": [],
    }
    run_tool = FakeRunTestsTool(output=output)
    registry = make_registry(run_tool)
    agent = TestingAgent(llm=MockProvider(), tools=registry)

    report = await agent.run_tests("/repo", test_command="pytest -q")

    assert isinstance(report, TestReport)
    assert report.all_passed is True
    assert run_tool.calls[0] == {"cwd": "/repo", "test_command": "pytest -q"}


@pytest.mark.asyncio
async def test_tester_handles_tool_error():
    run_tool = FakeRunTestsTool(raise_error="pytest binary not found")
    registry = make_registry(run_tool)
    agent = TestingAgent(llm=MockProvider(), tools=registry)

    report = await agent.run_tests("/repo")

    assert report.total == 0
    assert "pytest binary not found" in report.raw_output


# --------------------------------------------------------------------------
# SecurityAgent
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_security_agent_flags_real_issues(tmp_path: Path):
    unsafe = tmp_path / "unsafe.py"
    unsafe.write_text(
        "\n".join(
            [
                "API_KEY = 'sk-abcdef123456'",
                "import os",
                "os.system('rm -rf ' + user_input)",
                "import pickle",
                "data = pickle.loads(raw_bytes)",
            ]
        )
    )

    agent = SecurityAgent(llm=MockProvider())
    report = await agent.scan(str(tmp_path))

    rule_ids = {issue.rule_id for issue in report.issues}
    assert "hardcoded-secret" in rule_ids
    assert "os-system" in rule_ids
    assert "insecure-deserialization" in rule_ids
    assert report.blocking is True

    for issue in report.issues:
        assert issue.file == "unsafe.py"
        assert issue.line is not None


@pytest.mark.asyncio
async def test_security_agent_clean_repo_not_blocking(tmp_path: Path):
    (tmp_path / "clean.py").write_text("def add(a, b):\n    return a + b\n")

    agent = SecurityAgent(llm=MockProvider())
    report = await agent.scan(str(tmp_path))

    assert report.issues == []
    assert report.blocking is False
