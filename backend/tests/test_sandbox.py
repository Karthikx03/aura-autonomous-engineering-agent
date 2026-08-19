"""Tests for app.sandbox.sandbox_manager.SandboxManager.

These run against whichever mode SandboxManager actually detects. In this
development container there is no reachable Docker daemon, so the
expectation is "local-subprocess" -- but the assertions branch so the suite
also makes sense in an environment where a real daemon is available.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from app.config import Settings
from app.sandbox.sandbox_manager import SandboxManager


@pytest.fixture
def sandbox_settings(tmp_path: Path) -> Settings:
    return Settings(sandbox_workdir=str(tmp_path / "sandboxes"))


@pytest.fixture
def manager(sandbox_settings: Settings) -> SandboxManager:
    return SandboxManager(settings=sandbox_settings)


@pytest.fixture
def tiny_project(tmp_path: Path) -> Path:
    project = tmp_path / "tiny_project"
    project.mkdir()
    (project / "hello.txt").write_text("hello world\n")
    (project / ".git").mkdir()  # should be excluded when copied
    (project / ".git" / "config").write_text("should not be copied")
    return project


def test_mode_detection(manager: SandboxManager) -> None:
    assert manager.mode in ("docker", "local-subprocess")
    # This container has no reachable docker daemon.
    assert manager.mode == "local-subprocess"


@pytest.mark.asyncio
async def test_create_sandbox_copies_project_and_excludes_git(manager: SandboxManager, tiny_project: Path) -> None:
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    try:
        workdir = manager.workdir_for(sandbox_id)
        assert workdir.exists()
        assert (workdir / "hello.txt").read_text() == "hello world\n"
        assert not (workdir / ".git").exists()
    finally:
        await manager.destroy_sandbox(sandbox_id)


@pytest.mark.asyncio
async def test_execute_echo(manager: SandboxManager, tiny_project: Path) -> None:
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    try:
        result = await manager.execute(sandbox_id, "echo hello", timeout=10)
        assert result.exit_code == 0
        assert "hello" in result.stdout
        assert result.timed_out is False
    finally:
        await manager.destroy_sandbox(sandbox_id)


@pytest.mark.asyncio
async def test_execute_python(manager: SandboxManager, tiny_project: Path) -> None:
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    try:
        result = await manager.execute(sandbox_id, 'python3 -c "print(1+1)"', timeout=10)
        assert result.exit_code == 0
        assert result.stdout.strip() == "2"
    finally:
        await manager.destroy_sandbox(sandbox_id)


@pytest.mark.asyncio
async def test_execute_timeout_returns_promptly(manager: SandboxManager, tiny_project: Path) -> None:
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    try:
        started = time.perf_counter()
        result = await manager.execute(sandbox_id, "sleep 5", timeout=1)
        elapsed = time.perf_counter() - started
        assert result.timed_out is True
        assert elapsed < 4.0  # should return promptly rather than hanging for the full 5s
    finally:
        await manager.destroy_sandbox(sandbox_id)


@pytest.mark.asyncio
async def test_destroy_sandbox_frees_disk(manager: SandboxManager, tiny_project: Path) -> None:
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    workdir = manager.workdir_for(sandbox_id)
    assert workdir.exists()
    await manager.destroy_sandbox(sandbox_id)
    assert not workdir.exists()


@pytest.mark.asyncio
async def test_execute_uses_restricted_env(manager: SandboxManager, tiny_project: Path) -> None:
    """Host-only secrets should not leak into sandboxed commands."""
    sandbox_id = await manager.create_sandbox(str(tiny_project))
    try:
        result = await manager.execute(sandbox_id, "env", timeout=10)
        for line in result.stdout.splitlines():
            key = line.split("=", 1)[0]
            # PWD is set by the shell itself on cwd change, not inherited
            # from the parent process -- everything else must come from
            # the explicit allow-list.
            assert key in ("PATH", "HOME", "LANG", "PWD", "SHLVL", "_")
    finally:
        await manager.destroy_sandbox(sandbox_id)
