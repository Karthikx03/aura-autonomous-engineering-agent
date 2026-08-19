"""Thin, explicit wrapper around GitPython for the operations AURA needs.

Deliberately does not auto-``git init`` anywhere -- initializing a
repository the user did not ask for would be a surprising (and possibly
destructive, if they expected a plain-file workspace) side effect. Callers
that want a fresh repo must create it themselves before constructing a
``GitManager``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import git
from git import InvalidGitRepositoryError, NoSuchPathError


class NotAGitRepoError(RuntimeError):
    """Raised when a GitManager is asked to operate on a non-git directory."""


class GitManager:
    """Repository operations scoped to a single working tree."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = str(Path(repo_path))
        path = Path(self.repo_path)
        if not path.exists():
            raise NotAGitRepoError(f"repo_path does not exist: {repo_path}")
        try:
            self._repo = git.Repo(self.repo_path, search_parent_directories=False)
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            raise NotAGitRepoError(f"Not a git repository: {repo_path}") from exc

    # ------------------------------------------------------------------
    @property
    def repo(self) -> git.Repo:
        return self._repo

    def is_git_repo(self) -> bool:
        try:
            _ = self._repo.git_dir
            return True
        except Exception:  # noqa: BLE001
            return False

    def status(self) -> str:
        """Porcelain-format working tree status (empty string if clean)."""
        return self._repo.git.status("--porcelain")

    def diff(self, staged: bool = False) -> str:
        if staged:
            return self._repo.git.diff("--cached")
        return self._repo.git.diff()

    def log(self, n: int = 10) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        try:
            commits = list(self._repo.iter_commits(max_count=n))
        except ValueError:
            # "does not have any commits yet"
            return entries
        for commit in commits:
            entries.append(
                {
                    "sha": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                }
            )
        return entries

    def current_branch(self) -> str:
        try:
            return self._repo.active_branch.name
        except TypeError:
            # Detached HEAD state.
            return self._repo.head.commit.hexsha

    def capture_snapshot(self) -> dict[str, Any]:
        """Cheap point-in-time record of repo state, useful for before/after diffs."""
        try:
            head_sha = self._repo.head.commit.hexsha
        except (ValueError, git.exc.BadName):
            head_sha = None
        try:
            is_dirty = self._repo.is_dirty(untracked_files=True)
        except Exception:  # noqa: BLE001
            is_dirty = False
        return {
            "commit": head_sha,
            "status": self.status(),
            "is_dirty": is_dirty,
        }

    def commit(self, message: str, allow_empty: bool = False) -> str:
        """Stage everything and commit. Returns the new commit sha."""
        self._repo.git.add(A=True)
        has_staged_changes = bool(self._repo.git.diff("--cached", "--name-only").strip())
        if not has_staged_changes and not allow_empty:
            raise RuntimeError("Nothing to commit: working tree matches HEAD and allow_empty is False")
        commit_args: list[str] = ["-m", message]
        if allow_empty:
            commit_args.append("--allow-empty")
        self._repo.git.commit(*commit_args)
        return self._repo.head.commit.hexsha
