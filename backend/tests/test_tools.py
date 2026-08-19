"""Tests for the sandboxed file tools, command/test runners, and git tools."""
from __future__ import annotations

import textwrap

import pytest

from app.tools.command_tools import RunCommandTool, RunTestsTool
from app.tools.file_tools import (
    EditFileTool,
    ListDirectoryTool,
    ReadFileTool,
    SearchCodeTool,
    WriteFileTool,
    resolve_in_root,
)
from app.tools.git_tools import GitCommitTool, GitDiffTool, GitLogTool, GitStatusTool
from app.tools.registry import build_default_registry


# --------------------------------------------------------------------------
# File tools
# --------------------------------------------------------------------------


async def test_write_and_read_file_roundtrip(tmp_path):
    root = str(tmp_path)
    writer = WriteFileTool(root=root)
    reader = ReadFileTool(root=root)

    write_result = await writer.run(path="notes/hello.txt", content="hello world")
    assert write_result.ok
    assert write_result.output == {"path": "notes/hello.txt", "bytes_written": 11}

    read_result = await reader.run(path="notes/hello.txt")
    assert read_result.ok
    assert read_result.output == "hello world"


async def test_read_file_missing_raises_error_result(tmp_path):
    reader = ReadFileTool(root=str(tmp_path))
    result = await reader.run(path="does-not-exist.txt")
    assert not result.ok
    assert "No such file" in result.error


async def test_edit_file_replaces_all_occurrences_and_counts(tmp_path):
    target = tmp_path / "greeting.txt"
    target.write_text("hi hi hi", encoding="utf-8")

    editor = EditFileTool(root=str(tmp_path))
    result = await editor.run(path="greeting.txt", find="hi", replace="bye")
    assert result.ok
    assert result.output == {"path": "greeting.txt", "replacements": 3}
    assert target.read_text(encoding="utf-8") == "bye bye bye"


async def test_edit_file_raises_when_find_text_absent(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("nothing to see here", encoding="utf-8")

    editor = EditFileTool(root=str(tmp_path))
    with pytest.raises(ValueError):
        await editor._run(path="file.txt", find="missing", replace="x")


async def test_list_directory_recursive_skips_ignored_dirs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("a", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("x", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "a.pyc").write_text("x", encoding="utf-8")

    lister = ListDirectoryTool(root=str(tmp_path))
    result = await lister.run(path=".", recursive=True)
    assert result.ok
    assert "src/a.py" in result.output
    assert not any(".git" in p for p in result.output)
    assert not any("__pycache__" in p for p in result.output)


async def test_search_code_finds_matches_with_line_numbers(tmp_path):
    (tmp_path / "mod.py").write_text("def foo():\n    return 42\n", encoding="utf-8")

    searcher = SearchCodeTool(root=str(tmp_path))
    result = await searcher.run(query="def foo", path=".")
    assert result.ok
    assert len(result.output) == 1
    assert result.output[0]["file"] == "mod.py"
    assert result.output[0]["line"] == 1


async def test_search_code_regex_mode(tmp_path):
    (tmp_path / "mod.py").write_text("value = 123\nother = 456\n", encoding="utf-8")

    searcher = SearchCodeTool(root=str(tmp_path))
    result = await searcher.run(query=r"\d{3}", path=".", regex=True)
    assert result.ok
    assert len(result.output) == 2


@pytest.mark.parametrize(
    "escaping_path",
    ["../../etc/passwd", "../outside.txt", "/etc/passwd"],
)
def test_resolve_in_root_rejects_traversal(tmp_path, escaping_path):
    with pytest.raises(ValueError, match="path escapes sandbox root"):
        resolve_in_root(str(tmp_path), escaping_path)


async def test_read_file_tool_rejects_path_traversal(tmp_path):
    # Prove the security control end-to-end through the Tool.run() wrapper,
    # not just the helper function.
    secret_dir = tmp_path.parent / "secret_area"
    secret_dir.mkdir(exist_ok=True)
    (secret_dir / "secret.txt").write_text("top secret", encoding="utf-8")

    sandbox_root = tmp_path / "workspace"
    sandbox_root.mkdir()
    reader = ReadFileTool(root=str(sandbox_root))

    result = await reader.run(path=f"../secret_area/secret.txt")
    assert not result.ok
    assert "escapes sandbox root" in result.error


async def test_write_file_tool_rejects_path_traversal(tmp_path):
    sandbox_root = tmp_path / "workspace"
    sandbox_root.mkdir()
    writer = WriteFileTool(root=str(sandbox_root))

    result = await writer.run(path="../../evil.txt", content="pwned")
    assert not result.ok
    assert "escapes sandbox root" in result.error
    assert not (tmp_path.parent / "evil.txt").exists()


# --------------------------------------------------------------------------
# Command / test runner tools
# --------------------------------------------------------------------------


async def test_run_command_tool_captures_stdout_and_exit_code(tmp_path):
    tool = RunCommandTool()
    result = await tool.run(command="echo hello-aura", cwd=str(tmp_path))
    assert result.ok
    assert result.output["exit_code"] == 0
    assert "hello-aura" in result.output["stdout"]
    assert result.output["timed_out"] is False


async def test_run_command_tool_times_out(tmp_path):
    tool = RunCommandTool()
    result = await tool.run(command="sleep 5", cwd=str(tmp_path), timeout=1)
    assert result.ok  # the tool call itself succeeds; timeout is reported in output
    assert result.output["timed_out"] is True
    assert result.output["exit_code"] == -1


async def test_run_tests_tool_parses_pytest_summary(tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        textwrap.dedent(
            """
            def test_passing():
                assert 1 + 1 == 2

            def test_failing():
                assert 1 + 1 == 3
            """
        ),
        encoding="utf-8",
    )

    tool = RunTestsTool()
    result = await tool.run(cwd=str(tmp_path), test_command="pytest -q --no-header -p no:cacheprovider")
    assert result.ok
    output = result.output
    assert output["total"] == 2
    assert output["passed"] == 1
    assert output["failed"] == 1
    assert output["skipped"] == 0
    assert output["raw_output"]
    assert any("test_failing" in f for f in output["failures"])


async def test_run_tests_tool_degrades_gracefully_on_non_pytest_command(tmp_path):
    tool = RunTestsTool()
    result = await tool.run(cwd=str(tmp_path), test_command="echo not-a-test-runner")
    assert result.ok
    output = result.output
    assert output["total"] == 0
    assert output["passed"] == 0
    assert output["failed"] == 0
    assert output["skipped"] == 0
    assert "not-a-test-runner" in output["raw_output"]


# --------------------------------------------------------------------------
# Git tools
# --------------------------------------------------------------------------


def _init_repo_with_commit(tmp_path):
    import git

    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as config:
        config.set_value("user", "name", "AURA Test")
        config.set_value("user", "email", "aura-test@example.com")

    (tmp_path / "README.md").write_text("# Test repo\n", encoding="utf-8")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")
    return repo


async def test_git_status_reports_untracked_and_modified(tmp_path):
    repo = _init_repo_with_commit(tmp_path)
    (tmp_path / "README.md").write_text("# Test repo\nmodified\n", encoding="utf-8")
    (tmp_path / "new_file.txt").write_text("new", encoding="utf-8")

    tool = GitStatusTool()
    result = await tool.run(repo_path=str(tmp_path))
    assert result.ok
    assert result.output["is_dirty"] is True
    assert "new_file.txt" in result.output["untracked_files"]
    assert "README.md" in result.output["modified_files"]


async def test_git_diff_unstaged_and_staged(tmp_path):
    repo = _init_repo_with_commit(tmp_path)
    (tmp_path / "README.md").write_text("# Test repo\nmodified\n", encoding="utf-8")

    tool = GitDiffTool()
    unstaged = await tool.run(repo_path=str(tmp_path), staged=False)
    assert unstaged.ok
    assert "modified" in unstaged.output

    repo.index.add(["README.md"])
    staged = await tool.run(repo_path=str(tmp_path), staged=True)
    assert staged.ok
    assert "modified" in staged.output


async def test_git_log_returns_recent_commits(tmp_path):
    _init_repo_with_commit(tmp_path)

    tool = GitLogTool()
    result = await tool.run(repo_path=str(tmp_path), n=5)
    assert result.ok
    assert len(result.output) == 1
    entry = result.output[0]
    assert entry["message"] == "Initial commit"
    assert entry["author"] == "AURA Test"
    assert len(entry["sha"]) == 40
    assert entry["date"]


async def test_git_commit_creates_new_commit(tmp_path):
    _init_repo_with_commit(tmp_path)
    (tmp_path / "new_file.txt").write_text("new content", encoding="utf-8")

    tool = GitCommitTool()
    result = await tool.run(repo_path=str(tmp_path), message="Add new_file.txt")
    assert result.ok
    assert len(result.output["sha"]) == 40

    log_tool = GitLogTool()
    log_result = await log_tool.run(repo_path=str(tmp_path), n=5)
    assert len(log_result.output) == 2
    assert log_result.output[0]["message"] == "Add new_file.txt"


async def test_git_status_on_non_repo_returns_error(tmp_path):
    non_repo = tmp_path / "not_a_repo"
    non_repo.mkdir()
    tool = GitStatusTool()
    result = await tool.run(repo_path=str(non_repo))
    assert not result.ok
    assert "Not a git repository" in result.error


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------


def test_build_default_registry_registers_all_ten_tools(tmp_path):
    registry = build_default_registry(str(tmp_path))
    expected = {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "search_code",
        "run_command",
        "run_tests",
        "git_status",
        "git_diff",
        "git_log",
        "git_commit",
    }
    assert expected.issubset(set(registry.names()))


async def test_registry_call_dispatches_by_name(tmp_path):
    registry = build_default_registry(str(tmp_path))
    result = await registry.call("write_file", agent="tester", path="out.txt", content="data")
    assert result.ok
    assert result.output["path"] == "out.txt"
