"""Shell-command and test-runner tools.

Both run subprocesses via ``asyncio.create_subprocess_shell`` in their own
process group so a timeout can kill the whole tree (a shell command may
spawn children) rather than leaving orphans running.
"""
from __future__ import annotations

import asyncio
import os
import re
import signal
import time
from typing import Any

from app.tools.base import Tool

_SUMMARY_RE = re.compile(
    r"(?P<counts>(?:\d+ \w+(?:, )?)+)\s*in\s+(?P<duration>[\d.]+)s"
)
_COUNT_RE = re.compile(r"(\d+)\s+(passed|failed|skipped|error|errors|xfailed|xpassed)")
_FAILURE_LINE_RE = re.compile(r"^FAILED (\S+)", re.MULTILINE)


async def _run_subprocess(command: str, cwd: str, timeout: int) -> dict[str, Any]:
    started = time.perf_counter()
    process = await asyncio.create_subprocess_shell(
        command,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )
    timed_out = False
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
        exit_code = process.returncode if process.returncode is not None else -1
    except asyncio.TimeoutError:
        timed_out = True
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()
        stdout_bytes, stderr_bytes = b"", b""
        exit_code = -1

    duration = time.perf_counter() - started
    return {
        "stdout": stdout_bytes.decode("utf-8", errors="replace"),
        "stderr": stderr_bytes.decode("utf-8", errors="replace"),
        "exit_code": exit_code,
        "duration_seconds": duration,
        "timed_out": timed_out,
    }


class RunCommandTool(Tool):
    name = "run_command"
    description = "Run an arbitrary shell command in a given working directory."

    async def _run(self, command: str, cwd: str, timeout: int = 30) -> dict[str, Any]:
        return await _run_subprocess(command, cwd, timeout)


class RunTestsTool(Tool):
    name = "run_tests"
    description = "Run a project's test suite and parse a pytest-style summary."

    async def _run(self, cwd: str, test_command: str = "pytest -q") -> dict[str, Any]:
        result = await _run_subprocess(test_command, cwd, timeout=300)
        raw_output = result["stdout"] + result["stderr"]

        parsed = self._parse_pytest_summary(raw_output)
        failures = _FAILURE_LINE_RE.findall(raw_output)

        return {
            "total": parsed["total"],
            "passed": parsed["passed"],
            "failed": parsed["failed"],
            "skipped": parsed["skipped"],
            "duration_seconds": result["duration_seconds"],
            "coverage_percent": self._parse_coverage(raw_output),
            "raw_output": raw_output,
            "failures": failures,
        }

    @staticmethod
    def _parse_pytest_summary(output: str) -> dict[str, int]:
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        match = _SUMMARY_RE.search(output)
        if not match:
            return {"total": 0, **counts}
        for number, label in _COUNT_RE.findall(match.group("counts")):
            n = int(number)
            if label == "passed":
                counts["passed"] += n
            elif label in ("failed", "error", "errors"):
                counts["failed"] += n
            elif label in ("skipped", "xfailed", "xpassed"):
                counts["skipped"] += n
        total = counts["passed"] + counts["failed"] + counts["skipped"]
        return {"total": total, **counts}

    @staticmethod
    def _parse_coverage(output: str) -> float | None:
        match = re.search(r"TOTAL\s+(?:\d+\s+){2,}(\d+)%", output)
        if match:
            return float(match.group(1))
        match = re.search(r"(?:coverage|TOTAL).*?(\d+(?:\.\d+)?)%", output, re.IGNORECASE)
        return float(match.group(1)) if match else None
