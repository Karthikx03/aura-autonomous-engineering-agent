"""Convenience wiring: build a ``ToolRegistry`` with every AURA tool registered."""
from __future__ import annotations

from app.tools.base import ToolRegistry
from app.tools.command_tools import RunCommandTool, RunTestsTool
from app.tools.file_tools import (
    EditFileTool,
    ListDirectoryTool,
    ReadFileTool,
    SearchCodeTool,
    WriteFileTool,
)
from app.tools.git_tools import GitCommitTool, GitDiffTool, GitLogTool, GitStatusTool


def build_default_registry(repo_root: str) -> ToolRegistry:
    """Instantiate and register the full standard AURA toolset.

    File tools are sandboxed to ``repo_root``. The command/test/git tools
    take ``cwd``/``repo_path`` per-call (per the standardized contract other
    agents rely on), so they need no root binding here.
    """
    registry = ToolRegistry()
    registry.register(ReadFileTool(root=repo_root))
    registry.register(WriteFileTool(root=repo_root))
    registry.register(EditFileTool(root=repo_root))
    registry.register(ListDirectoryTool(root=repo_root))
    registry.register(SearchCodeTool(root=repo_root))
    registry.register(RunCommandTool())
    registry.register(RunTestsTool())
    registry.register(GitStatusTool())
    registry.register(GitDiffTool())
    registry.register(GitLogTool())
    registry.register(GitCommitTool())
    return registry
