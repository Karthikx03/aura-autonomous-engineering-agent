"""Filesystem tools, every one of them sandboxed to a bound ``root`` directory.

Each tool is constructed with ``root`` (the repository/workspace root an
agent is allowed to touch) and resolves every ``path`` argument against it.
Any path that would escape ``root`` — via ``..`` traversal, an absolute
path pointing elsewhere, or a symlink — is rejected with ``ValueError``.
This is a real security boundary, not a convenience check, so it is applied
uniformly through :func:`resolve_in_root` rather than re-implemented per
tool.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from app.tools.base import Tool

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}


def resolve_in_root(root: str, path: str) -> Path:
    """Resolve ``path`` relative to ``root``, rejecting sandbox escapes."""
    root_resolved = Path(root).resolve()
    candidate = Path(root_resolved, path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise ValueError("path escapes sandbox root") from None
    return candidate


def _iter_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            yield Path(dirpath) / filename


class ReadFileTool(Tool):
    name = "read_file"
    description = "Read the full contents of a text file within the sandbox root."

    def __init__(self, root: str) -> None:
        self.root = root

    async def _run(self, path: str) -> str:
        target = resolve_in_root(self.root, path)
        if not target.is_file():
            raise FileNotFoundError(f"No such file: {path}")
        return target.read_text(encoding="utf-8", errors="replace")


class WriteFileTool(Tool):
    name = "write_file"
    description = "Write (create or overwrite) a text file within the sandbox root."

    def __init__(self, root: str) -> None:
        self.root = root

    async def _run(self, path: str, content: str) -> dict[str, Any]:
        target = resolve_in_root(self.root, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": path, "bytes_written": len(content.encode("utf-8"))}


class EditFileTool(Tool):
    name = "edit_file"
    description = "Replace occurrences of a literal string within a file within the sandbox root."

    def __init__(self, root: str) -> None:
        self.root = root

    async def _run(self, path: str, find: str, replace: str) -> dict[str, Any]:
        target = resolve_in_root(self.root, path)
        if not target.is_file():
            raise FileNotFoundError(f"No such file: {path}")
        original = target.read_text(encoding="utf-8", errors="replace")
        count = original.count(find)
        if count == 0:
            raise ValueError(f"find text not found in {path}")
        updated = original.replace(find, replace)
        target.write_text(updated, encoding="utf-8")
        return {"path": path, "replacements": count}


class ListDirectoryTool(Tool):
    name = "list_directory"
    description = "List files under a directory within the sandbox root."

    def __init__(self, root: str) -> None:
        self.root = root

    async def _run(self, path: str = ".", recursive: bool = False) -> list[str]:
        base = resolve_in_root(self.root, path)
        if not base.exists():
            raise FileNotFoundError(f"No such directory: {path}")
        root_resolved = Path(self.root).resolve()
        results: list[str] = []
        if recursive:
            for file_path in sorted(_iter_files(base)):
                results.append(str(file_path.relative_to(root_resolved)))
        else:
            for entry in sorted(base.iterdir()):
                if entry.name in SKIP_DIRS:
                    continue
                results.append(str(entry.relative_to(root_resolved)))
        return results


class SearchCodeTool(Tool):
    name = "search_code"
    description = "Search text files under a directory for a query string or regex."

    MAX_RESULTS = 500

    def __init__(self, root: str) -> None:
        self.root = root

    async def _run(self, query: str, path: str = ".", regex: bool = False) -> list[dict[str, Any]]:
        import re

        base = resolve_in_root(self.root, path)
        root_resolved = Path(self.root).resolve()
        pattern = re.compile(query) if regex else None

        matches: list[dict[str, Any]] = []
        for file_path in sorted(_iter_files(base)):
            if len(matches) >= self.MAX_RESULTS:
                break
            try:
                text = file_path.read_text(encoding="utf-8", errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                found = pattern.search(line) if pattern else (query in line)
                if found:
                    matches.append(
                        {
                            "file": str(file_path.relative_to(root_resolved)),
                            "line": lineno,
                            "text": line.strip(),
                        }
                    )
                    if len(matches) >= self.MAX_RESULTS:
                        break
        return matches
