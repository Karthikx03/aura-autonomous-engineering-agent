"""Git tools, implemented directly against GitPython.

Self-contained on purpose: these do not import from ``app.git_integration``
(a sibling module owned by another engineer) to avoid a build-order
dependency. Any incidental duplication of logic there is expected and fine.
"""
from __future__ import annotations

from typing import Any

from app.tools.base import Tool


def _open_repo(repo_path: str):
    import git

    try:
        return git.Repo(repo_path)
    except git.InvalidGitRepositoryError as exc:
        raise ValueError(f"Not a git repository: {repo_path}") from exc
    except git.NoSuchPathError as exc:
        raise ValueError(f"No such path: {repo_path}") from exc


class GitStatusTool(Tool):
    name = "git_status"
    description = "Show the working tree status (modified/untracked/staged files) of a git repo."

    async def _run(self, repo_path: str) -> dict[str, Any]:
        repo = _open_repo(repo_path)
        return {
            "branch": repo.active_branch.name if not repo.head.is_detached else None,
            "is_dirty": repo.is_dirty(untracked_files=True),
            "untracked_files": list(repo.untracked_files),
            "modified_files": [item.a_path for item in repo.index.diff(None)],
            "staged_files": [item.a_path for item in repo.index.diff("HEAD")] if repo.head.is_valid() else [],
        }


class GitDiffTool(Tool):
    name = "git_diff"
    description = "Show the diff of unstaged (or staged) changes in a git repo."

    async def _run(self, repo_path: str, staged: bool = False) -> str:
        repo = _open_repo(repo_path)
        if staged:
            return repo.git.diff("--cached")
        return repo.git.diff()


class GitLogTool(Tool):
    name = "git_log"
    description = "Show the most recent commits of a git repo."

    async def _run(self, repo_path: str, n: int = 10) -> list[dict[str, Any]]:
        repo = _open_repo(repo_path)
        if not repo.head.is_valid():
            return []
        entries = []
        for commit in repo.iter_commits(max_count=n):
            entries.append(
                {
                    "sha": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name or "",
                    "date": commit.committed_datetime.isoformat(),
                }
            )
        return entries


class GitCommitTool(Tool):
    name = "git_commit"
    description = "Stage all changes and create a commit in a git repo."

    async def _run(self, repo_path: str, message: str) -> dict[str, str]:
        repo = _open_repo(repo_path)
        repo.git.add(A=True)
        commit = repo.index.commit(message)
        return {"sha": commit.hexsha}
