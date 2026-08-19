"""SecurityAgent: deterministic static-analysis scan, no LLM involved.

A small rule table of regexes is applied to source files to catch common,
concrete security smells (hardcoded secrets, dangerous eval/exec, shell
injection, insecure deserialization, disabled TLS verification, naive SQL
string interpolation, path traversal literals). This is real pattern-based
detection -- it is exercised end-to-end in tests against files written to a
temp directory.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from app.agents.base import BaseAgent
from app.orchestrator.state import SecurityIssue, SecurityReport

_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build"}
_SCAN_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx"}

_RULES: list[tuple[str, re.Pattern, str, str]] = [
    (
        "hardcoded-secret",
        re.compile(r"(?i)(api_key|secret|password|token)\s*=\s*['\"][^'\"]{6,}['\"]"),
        "high",
        "Possible hardcoded secret or credential.",
    ),
    (
        "aws-access-key",
        re.compile(r"AKIA[0-9A-Z]{16}"),
        "critical",
        "Possible AWS access key literal.",
    ),
    (
        "dangerous-eval",
        re.compile(r"\beval\s*\("),
        "high",
        "Use of eval() can allow arbitrary code execution.",
    ),
    (
        "dangerous-exec",
        re.compile(r"\bexec\s*\("),
        "high",
        "Use of exec() can allow arbitrary code execution.",
    ),
    (
        "os-system",
        re.compile(r"os\.system\("),
        "high",
        "os.system() is prone to shell injection; prefer subprocess with a list of args.",
    ),
    (
        "shell-true-subprocess",
        re.compile(r"subprocess\.(Popen|call|run)\([^)]*shell\s*=\s*True"),
        "high",
        "subprocess call with shell=True is prone to shell injection.",
    ),
    (
        "insecure-deserialization",
        re.compile(r"pickle\.loads\("),
        "high",
        "pickle.loads() on untrusted input allows arbitrary code execution.",
    ),
    (
        "unsafe-yaml-load",
        re.compile(r"yaml\.load\((?!.*Loader\s*=\s*yaml\.SafeLoader)"),
        "medium",
        "yaml.load() without SafeLoader can execute arbitrary code.",
    ),
    (
        "tls-verification-disabled",
        re.compile(r"verify\s*=\s*False"),
        "high",
        "TLS certificate verification disabled.",
    ),
    (
        "sql-string-interpolation",
        re.compile(
            r"(?i)((SELECT|INSERT|UPDATE|DELETE).*%s)|(f[\"'].*\{.*\}.*(SELECT|INSERT|UPDATE|DELETE))"
        ),
        "high",
        "Possible SQL injection via naive string formatting; use parameterized queries.",
    ),
    (
        "path-traversal-literal",
        re.compile(r"\.\./\.\./"),
        "medium",
        "Path traversal literal detected.",
    ),
]


class SecurityAgent(BaseAgent):
    name = "security"

    async def scan(self, repo_path: str) -> SecurityReport:
        self.emit("Security scan started", repo_path=repo_path)

        root = Path(repo_path)
        issues: list[SecurityIssue] = []

        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]
            for filename in filenames:
                if Path(filename).suffix not in _SCAN_EXTENSIONS:
                    continue
                file_path = Path(dirpath) / filename
                rel_path = os.path.relpath(file_path, root)
                try:
                    text = file_path.read_text(errors="ignore")
                except OSError:
                    continue
                for line_number, line in enumerate(text.splitlines(), start=1):
                    for rule_id, pattern, severity, message in _RULES:
                        if pattern.search(line):
                            issues.append(
                                SecurityIssue(
                                    rule_id=rule_id,
                                    severity=severity,
                                    file=rel_path,
                                    line=line_number,
                                    message=message,
                                )
                            )

        report = SecurityReport(issues=issues)
        self.emit("Security scan completed", issues=len(issues), blocking=report.blocking)
        return report
