#!/usr/bin/env python3
"""AURA-Bench runner.

Validates that every task under aura-bench/tasks/ has a genuine,
mechanically-verifiable bug: the starter/ code must make tests/test_task.py
FAIL, and the solution/ code must make the exact same test file PASS.

Usage:
    python3 runner.py --list
    python3 runner.py --validate

Both commands operate purely on real subprocess runs of pytest against
copies of the task fixtures - nothing here fabricates results.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Optional

THIS_FILE = Path(__file__).resolve()
BENCH_ROOT = THIS_FILE.parent.parent
TASKS_DIR = BENCH_ROOT / "tasks"
RESULTS_DIR = BENCH_ROOT / "results"


def discover_tasks() -> list[Path]:
    """Return sorted task directories under aura-bench/tasks/."""
    if not TASKS_DIR.exists():
        return []
    return sorted(p for p in TASKS_DIR.iterdir() if p.is_dir() and (p / "task.json").exists())


def load_task_meta(task_dir: Path) -> dict:
    with open(task_dir / "task.json", "r", encoding="utf-8") as fh:
        return json.load(fh)


def _prepare_workdir(task_dir: Path, variant: str, workdir: Path) -> None:
    """Copy the given variant (starter/ or solution/) of a task plus its
    test file into workdir, so pytest can import the code under test and
    the test file directly (they live side by side, no packaging needed)."""
    variant_dir = task_dir / variant
    for item in variant_dir.iterdir():
        dest = workdir / item.name
        if item.is_dir():
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)

    tests_src = task_dir / "tests" / "test_task.py"
    shutil.copy2(tests_src, workdir / "test_task.py")


def _run_pytest(workdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "test_task.py", "-q"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
        timeout=120,
    )


def validate_task(task_dir: Path) -> dict:
    """Run starter (expect FAIL) then solution (expect PASS) for one task."""
    task_id = task_dir.name
    result = {
        "task_id": task_id,
        "starter_fails_as_expected": False,
        "solution_passes": False,
        "starter_returncode": None,
        "solution_returncode": None,
    }

    with tempfile.TemporaryDirectory(prefix=f"aurabench-{task_id}-starter-") as tmp:
        _prepare_workdir(task_dir, "starter", Path(tmp))
        proc = _run_pytest(Path(tmp))
        result["starter_returncode"] = proc.returncode
        result["starter_fails_as_expected"] = proc.returncode != 0
        result["starter_output_tail"] = "\n".join(proc.stdout.strip().splitlines()[-15:])

    with tempfile.TemporaryDirectory(prefix=f"aurabench-{task_id}-solution-") as tmp:
        _prepare_workdir(task_dir, "solution", Path(tmp))
        proc = _run_pytest(Path(tmp))
        result["solution_returncode"] = proc.returncode
        result["solution_passes"] = proc.returncode == 0
        result["solution_output_tail"] = "\n".join(proc.stdout.strip().splitlines()[-15:])

    result["harness_valid"] = result["starter_fails_as_expected"] and result["solution_passes"]
    return result


def run_validate() -> dict:
    task_dirs = discover_tasks()
    per_task_results = []
    for task_dir in task_dirs:
        print(f"Validating {task_dir.name} ...", flush=True)
        res = validate_task(task_dir)
        status = "OK" if res["harness_valid"] else "FAILED"
        print(
            f"  starter_fails_as_expected={res['starter_fails_as_expected']} "
            f"solution_passes={res['solution_passes']}  -> {status}"
        )
        per_task_results.append(res)

    harness_valid_count = sum(1 for r in per_task_results if r["harness_valid"])
    report = {
        "total_tasks": len(per_task_results),
        "harness_valid_count": harness_valid_count,
        "generated_at_unix": time.time(),
        "tasks": per_task_results,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / "validation_report.json"
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print()
    print(f"Wrote {out_path}")
    print(f"Summary: {harness_valid_count}/{len(per_task_results)} tasks have a genuine, "
          f"reproducible starter-fails / solution-passes harness.")
    return report


def run_list() -> None:
    task_dirs = discover_tasks()
    for task_dir in task_dirs:
        meta = load_task_meta(task_dir)
        print(f"{meta['id']:28s} [{meta['difficulty']:6s}] {meta['category']:15s} {meta['title']}")
    print(f"\n{len(task_dirs)} tasks total")


class BenchRunner:
    """Extensibility hook for driving aura-bench tasks through a real
    solving agent (e.g. AURA's Orchestrator), not just the static
    starter/solution validation performed by --validate.

    run_task() copies a task's starter/ into a scratch workdir, optionally
    invokes solve_fn(workdir) to let an external agent attempt a fix in
    place, then runs the task's real pytest suite against whatever ended
    up in workdir and reports genuine results - nothing here is faked.
    """

    def __init__(self, tasks_dir: Path = TASKS_DIR):
        self.tasks_dir = Path(tasks_dir)

    def run_task(self, task_id: str, solve_fn: Optional[Callable[[str], None]] = None) -> dict:
        task_dir = self.tasks_dir / task_id
        if not task_dir.exists():
            raise FileNotFoundError(f"Unknown task: {task_id}")

        start = time.time()
        with tempfile.TemporaryDirectory(prefix=f"aurabench-run-{task_id}-") as tmp:
            workdir = Path(tmp)
            _prepare_workdir(task_dir, "starter", workdir)

            files_before = {p: p.stat().st_mtime for p in workdir.rglob("*") if p.is_file()}

            iterations = 0
            security_issues: list = []
            if solve_fn is not None:
                # A real solve_fn (e.g. the live Orchestrator) is expected to
                # edit files in workdir. We can't know its internal
                # iteration count or run a security scan from here, so we
                # only count that we invoked it once; a real integration
                # should have solve_fn report its own iteration count back.
                solve_fn(str(workdir))
                iterations = 1
            # else: no solver was wired in, so iterations/security_issues
            # stay at their honest defaults (0/[]) rather than being faked.

            proc = _run_pytest(workdir)
            elapsed = time.time() - start

            files_changed = [
                str(p.relative_to(workdir))
                for p in workdir.rglob("*")
                if p.is_file() and files_before.get(p) != p.stat().st_mtime
            ]

            tests_passed = 0
            tests_failed = 0
            import re

            summary_lines = [
                line.strip()
                for line in proc.stdout.splitlines()
                if re.search(r"\d+ (passed|failed|error)", line)
            ]
            if summary_lines:
                # The final summary line, e.g. "2 passed in 0.01s" or
                # "1 failed, 1 passed in 0.02s".
                for count, label in re.findall(r"(\d+) (passed|failed|error)", summary_lines[-1]):
                    if label == "passed":
                        tests_passed += int(count)
                    else:
                        tests_failed += int(count)

            return {
                "task_id": task_id,
                "success": proc.returncode == 0,
                "time_seconds": elapsed,
                "iterations": iterations,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "files_changed": files_changed,
                "security_issues": security_issues,
                "returncode": proc.returncode,
                "stdout_tail": "\n".join(proc.stdout.strip().splitlines()[-15:]),
            }


def main() -> int:
    parser = argparse.ArgumentParser(description="AURA-Bench task runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--validate", action="store_true", help="Validate all tasks' starter/solution harness")
    group.add_argument("--list", action="store_true", help="List all available tasks")
    args = parser.parse_args()

    if args.list:
        run_list()
        return 0

    if args.validate:
        report = run_validate()
        return 0 if report["harness_valid_count"] == report["total_tasks"] else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
