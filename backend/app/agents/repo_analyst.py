"""RepoAnalystAgent: builds a structural RepoMap of a repository.

The structural facts (languages, frameworks, dependencies, test files, git
presence, file counts) are computed for real by walking the filesystem --
never guessed by an LLM. An LLM call is used only, optionally, to produce a
short natural-language ``summary`` string layered on top of those facts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from app.agents.base import BaseAgent
from app.llm.base import LLMMessage
from app.orchestrator.state import RepoMap

_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache", "dist", "build"}

_EXT_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
}

_TEST_PATTERNS = (
    lambda name: name.startswith("test_") and name.endswith(".py"),
    lambda name: name.endswith("_test.py"),
    lambda name: name.endswith(".test.ts") or name.endswith(".test.tsx"),
    lambda name: name.endswith(".spec.ts") or name.endswith(".spec.tsx"),
    lambda name: name.endswith(".test.js") or name.endswith(".test.jsx"),
)

_SYSTEM_PROMPT = (
    "You are the repository analyst agent of AURA. Given structural facts "
    "about a repository, write a concise one-to-two sentence natural-language "
    "summary of what the repository is and how it's built. Respond as a "
    'single JSON object: {"summary": "..."}.'
)


class RepoAnalystAgent(BaseAgent):
    name = "repo_analyst"

    async def analyze(self, repo_path: str) -> RepoMap:
        self.emit("Repository analysis started", repo_path=repo_path)

        root = Path(repo_path)
        languages: set[str] = set()
        test_files: list[str] = []
        file_count = 0

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                file_count += 1
                ext = Path(filename).suffix
                if ext in _EXT_LANGUAGE:
                    languages.add(_EXT_LANGUAGE[ext])
                if any(pattern(filename) for pattern in _TEST_PATTERNS):
                    rel = os.path.relpath(os.path.join(dirpath, filename), root)
                    test_files.append(rel)

        frameworks: set[str] = set()
        dependencies: list[str] = []

        requirements_txt = root / "requirements.txt"
        if requirements_txt.exists():
            deps = self._parse_requirements(requirements_txt)
            dependencies.extend(deps)
            frameworks |= self._detect_python_frameworks(deps)

        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            text = pyproject.read_text(errors="ignore")
            dependencies.append("pyproject.toml")
            frameworks |= self._detect_python_frameworks([text.lower()])

        package_json = root / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(errors="ignore"))
                deps = list(data.get("dependencies", {}).keys()) + list(data.get("devDependencies", {}).keys())
                dependencies.extend(deps)
                frameworks |= self._detect_js_frameworks(deps)
            except json.JSONDecodeError:
                pass

        go_mod = root / "go.mod"
        if go_mod.exists():
            dependencies.append("go.mod")
            frameworks.add("go-modules")

        has_git = (root / ".git").exists()

        repo_map = RepoMap(
            root=str(root),
            languages=sorted(languages),
            frameworks=sorted(frameworks),
            dependencies=sorted(set(dependencies)),
            test_files=sorted(test_files),
            has_git=has_git,
            file_count=file_count,
            summary="",
        )

        repo_map.summary = await self._summarize(repo_map)

        self.emit(
            "Repository analysis completed",
            languages=repo_map.languages,
            file_count=repo_map.file_count,
            has_git=repo_map.has_git,
        )
        return repo_map

    async def _summarize(self, repo_map: RepoMap) -> str:
        prompt = (
            "Summarize this repository for the analysis report.\n"
            f"languages={repo_map.languages}\n"
            f"frameworks={repo_map.frameworks}\n"
            f"file_count={repo_map.file_count}\n"
            f"has_git={repo_map.has_git}\n"
            f"test_files_count={len(repo_map.test_files)}"
        )
        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]
        try:
            response = await self.llm.complete(messages, json_mode=True)
            parsed = json.loads(response.content)
            summary = parsed.get("summary") if isinstance(parsed, dict) else None
            if isinstance(summary, str) and summary.strip():
                return summary.strip()
        except Exception as exc:
            self.emit("Repo summary generation failed, using structural fallback", error=str(exc))
        return (
            f"Repository with {repo_map.file_count} files spanning "
            f"{', '.join(repo_map.languages) or 'no detected languages'}."
        )

    @staticmethod
    def _parse_requirements(path: Path) -> list[str]:
        deps = []
        for line in path.read_text(errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name = line.split("==")[0].split(">=")[0].split("<=")[0].split("[")[0].strip()
            if name:
                deps.append(name)
        return deps

    @staticmethod
    def _detect_python_frameworks(deps: list[str]) -> set[str]:
        joined = " ".join(d.lower() for d in deps)
        frameworks = set()
        mapping = {
            "fastapi": "fastapi",
            "django": "django",
            "flask": "flask",
            "pytest": "pytest",
            "sqlalchemy": "sqlalchemy",
            "celery": "celery",
            "pydantic": "pydantic",
        }
        for needle, label in mapping.items():
            if needle in joined:
                frameworks.add(label)
        return frameworks

    @staticmethod
    def _detect_js_frameworks(deps: list[str]) -> set[str]:
        lowered = {d.lower() for d in deps}
        frameworks = set()
        mapping = {
            "react": "react",
            "next": "nextjs",
            "vue": "vue",
            "express": "express",
            "svelte": "svelte",
            "jest": "jest",
            "vite": "vite",
        }
        for needle, label in mapping.items():
            if any(needle in dep for dep in lowered):
                frameworks.add(label)
        return frameworks
