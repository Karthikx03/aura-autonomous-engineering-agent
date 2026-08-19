"""Tests for app.git_integration.git_manager.GitManager."""
from __future__ import annotations

from pathlib import Path

import git
import pytest

from app.git_integration.git_manager import GitManager, NotAGitRepoError


@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    repo = git.Repo.init(tmp_path)
    with repo.config_writer() as writer:
        writer.set_value("user", "name", "AURA Test")
        writer.set_value("user", "email", "aura-test@example.com")
    # Seed an initial commit so `current_branch`/`log` have something to
    # work with without relying on the "no commits yet" edge case.
    (tmp_path / "README.md").write_text("initial\n")
    repo.git.add(A=True)
    repo.git.commit("-m", "initial commit")
    return tmp_path


def test_not_a_git_repo_raises(tmp_path: Path) -> None:
    plain_dir = tmp_path / "not_a_repo"
    plain_dir.mkdir()
    with pytest.raises(NotAGitRepoError):
        GitManager(str(plain_dir))


def test_missing_path_raises(tmp_path: Path) -> None:
    with pytest.raises(NotAGitRepoError):
        GitManager(str(tmp_path / "does_not_exist"))


def test_is_git_repo(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    assert manager.is_git_repo() is True


def test_status_and_diff_reflect_working_tree_changes(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    assert manager.status() == ""
    assert manager.diff() == ""

    (repo_path / "feature.py").write_text("print('hello')\n")
    status = manager.status()
    assert "feature.py" in status

    (repo_path / "README.md").write_text("initial\nmodified\n")
    diff = manager.diff()
    assert "modified" in diff


def test_commit_returns_sha_and_appears_in_log(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    (repo_path / "feature.py").write_text("print('hello')\n")

    sha = manager.commit("Add feature.py")
    assert isinstance(sha, str)
    assert len(sha) == 40

    log_entries = manager.log(n=5)
    assert log_entries[0]["sha"] == sha
    assert log_entries[0]["message"] == "Add feature.py"
    assert log_entries[0]["author"] == "AURA Test"
    assert len(log_entries) == 2  # the seeded initial commit + this one


def test_commit_with_nothing_to_commit_raises(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    with pytest.raises(RuntimeError):
        manager.commit("Nothing changed")


def test_commit_allow_empty(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    sha = manager.commit("Empty commit", allow_empty=True)
    assert isinstance(sha, str)
    assert len(sha) == 40


def test_current_branch(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    branch = manager.current_branch()
    assert isinstance(branch, str)
    assert branch  # non-empty


def test_capture_snapshot_before_after_differ(repo_path: Path) -> None:
    manager = GitManager(str(repo_path))
    before = manager.capture_snapshot()
    assert before["is_dirty"] is False

    (repo_path / "feature.py").write_text("print('hello')\n")
    dirty_snapshot = manager.capture_snapshot()
    assert dirty_snapshot["is_dirty"] is True
    assert dirty_snapshot["commit"] == before["commit"]

    new_sha = manager.commit("Add feature.py")
    after = manager.capture_snapshot()
    assert after["commit"] == new_sha
    assert after["commit"] != before["commit"]
    assert after["is_dirty"] is False
