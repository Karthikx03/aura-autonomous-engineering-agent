"""Isolated execution environment for agent-run commands (tests, builds, ...).

AURA agents frequently need to run arbitrary shell commands (installing
dependencies, running a test suite, executing a script the CoderAgent just
wrote) against a copy of the target repository. Running that directly on
the host process would be a serious security hole -- ``SandboxManager``
gives every task run its own throwaway workdir and, when a Docker daemon is
reachable, its own container with resource limits and no network access.

Two execution modes:

* ``"docker"`` -- a real container boundary (cgroups, its own filesystem,
  optionally no network). Used whenever a Docker daemon is reachable.
* ``"local-subprocess"`` -- a **best-effort** fallback used when no daemon
  is available (e.g. this development container, which ships the ``docker``
  CLI/SDK but has no ``dockerd`` running). Commands run as a real OS
  subprocess in its own temp directory and process group, with
  ``RLIMIT_CPU``/``RLIMIT_AS`` applied where the platform allows it and a
  trimmed-down environment. This is NOT a security sandbox -- it does not
  isolate the filesystem, network, or kernel from the host. Anything that
  reports on AURA's security posture (see SECURITY.md) must say so plainly;
  ``SandboxManager.mode`` is public specifically so callers can surface it.

Both code paths are complete and independently testable. Only the
local-subprocess path can actually be exercised in this container because
there is no reachable Docker daemon here.
"""
from __future__ import annotations

import asyncio
import logging
import os
import resource
import shutil
import signal
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings, get_settings

logger = logging.getLogger("aura.sandbox")

# Directories we never want to copy into a sandbox: version control
# metadata, dependency caches, and bytecode caches are large, irrelevant to
# execution, and can leak host-only state (e.g. .git hooks).
_EXCLUDED_DIR_NAMES = {".git", "node_modules", "__pycache__", ".venv", ".mypy_cache", ".pytest_cache"}

# The subprocess fallback gets a deliberately minimal environment so that
# host secrets (API keys, cloud credentials, etc.) sitting in the parent
# process's environment are not implicitly handed to agent-run commands.
_ALLOWED_ENV_KEYS = ("PATH", "HOME", "LANG")


@dataclass
class ExecResult:
    """Outcome of running one command inside a sandbox."""

    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_seconds: float = 0.0
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return not self.timed_out and self.exit_code == 0


@dataclass
class _Sandbox:
    """Internal bookkeeping for one active sandbox instance."""

    sandbox_id: str
    workdir: Path
    container_id: str | None = None  # only set in docker mode
    created_at: float = field(default_factory=time.time)


def _ignore_excluded(directory: str, names: list[str]) -> list[str]:
    return [n for n in names if n in _EXCLUDED_DIR_NAMES]


class SandboxManager:
    """Creates, drives, and tears down isolated execution environments.

    On construction, probes for a live Docker daemon. If one answers a
    ``ping``, ``self.mode == "docker"`` and all sandboxes are real
    containers. Otherwise ``self.mode == "local-subprocess"`` and sandboxes
    are plain temp directories with commands run as restricted subprocesses.
    The probe never raises -- any failure (daemon not running, docker SDK
    not usable, permission denied, ...) is treated as "docker unavailable".
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._sandboxes: dict[str, _Sandbox] = {}
        self._docker_client = None
        self.mode = self._detect_mode()
        logger.info("SandboxManager initialized in '%s' mode", self.mode)

    # ------------------------------------------------------------------
    # Mode detection
    # ------------------------------------------------------------------
    def _detect_mode(self) -> str:
        try:
            import docker  # local import: keep the dependency optional at runtime

            client = docker.from_env()
            client.ping()
        except Exception as exc:  # noqa: BLE001 - genuinely any failure means "no docker"
            logger.info("Docker daemon not reachable (%s); falling back to local-subprocess sandbox mode", exc)
            self._docker_client = None
            return "local-subprocess"
        self._docker_client = client
        return "docker"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def create_sandbox(self, project_path: str) -> str:
        """Create a new sandbox workdir and copy the project into it.

        Returns the ``sandbox_id`` used by every other method. This does
        the same bookkeeping in both modes -- the docker-vs-subprocess
        distinction only shows up in ``execute``.
        """
        sandbox_id = uuid.uuid4().hex[:16]
        root = Path(self.settings.sandbox_workdir)
        root.mkdir(parents=True, exist_ok=True)
        workdir = root / sandbox_id
        self._sandboxes[sandbox_id] = _Sandbox(sandbox_id=sandbox_id, workdir=workdir)
        await self.copy_project(sandbox_id, project_path)
        return sandbox_id

    async def copy_project(self, sandbox_id: str, project_path: str) -> None:
        """(Re-)copy ``project_path`` into the sandbox's workdir."""
        sandbox = self._require_sandbox(sandbox_id)
        src = Path(project_path)
        if not src.exists():
            raise FileNotFoundError(f"project_path does not exist: {project_path}")

        def _copy() -> None:
            if sandbox.workdir.exists():
                shutil.rmtree(sandbox.workdir, ignore_errors=True)
            if src.is_dir():
                shutil.copytree(src, sandbox.workdir, ignore=_ignore_excluded)
            else:
                sandbox.workdir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, sandbox.workdir / src.name)

        await asyncio.to_thread(_copy)

    async def execute(self, sandbox_id: str, command: str, timeout: int | None = None) -> ExecResult:
        """Run ``command`` inside the sandbox and return its result.

        Never raises on command failure or timeout -- both are reported
        through ``ExecResult`` (``exit_code``/``timed_out``) so callers
        (agents) can inspect and react to them programmatically.
        """
        sandbox = self._require_sandbox(sandbox_id)
        effective_timeout = timeout if timeout is not None else self.settings.sandbox_timeout_seconds
        if self.mode == "docker":
            return await self._execute_docker(sandbox, command, effective_timeout)
        return await self._execute_subprocess(sandbox, command, effective_timeout)

    async def destroy_sandbox(self, sandbox_id: str) -> None:
        """Remove all resources (temp dir, and container if any) for a sandbox."""
        sandbox = self._sandboxes.pop(sandbox_id, None)
        if sandbox is None:
            return
        if sandbox.container_id and self._docker_client is not None:
            try:
                container = self._docker_client.containers.get(sandbox.container_id)
                container.remove(force=True)
            except Exception:  # noqa: BLE001 - already gone / daemon unreachable is fine
                pass
        await asyncio.to_thread(shutil.rmtree, sandbox.workdir, True)

    # ------------------------------------------------------------------
    # Docker execution
    # ------------------------------------------------------------------
    async def _execute_docker(self, sandbox: _Sandbox, command: str, timeout: int) -> ExecResult:
        return await asyncio.to_thread(self._execute_docker_sync, sandbox, command, timeout)

    def _execute_docker_sync(self, sandbox: _Sandbox, command: str, timeout: int) -> ExecResult:
        client = self._docker_client
        assert client is not None
        started = time.perf_counter()
        container = None
        try:
            container = client.containers.run(
                image="python:3.12-slim",
                command=["sh", "-c", command],
                volumes={str(sandbox.workdir): {"bind": "/workspace", "mode": "rw"}},
                working_dir="/workspace",
                mem_limit=f"{self.settings.sandbox_memory_limit_mb}m",
                nano_cpus=int(self.settings.sandbox_cpu_limit * 1_000_000_000),
                network_disabled=self.settings.sandbox_network_disabled,
                detach=True,
                stdout=True,
                stderr=True,
            )
            sandbox.container_id = container.id
            timed_out = False
            try:
                wait_result = container.wait(timeout=timeout)
                if isinstance(wait_result, dict):
                    exit_code = int(wait_result.get("StatusCode", -1))
                else:
                    exit_code = int(wait_result)
            except Exception:
                # docker-py raises a requests ReadTimeout (or ConnectionError
                # wrapping one) when the container outlives `timeout`.
                timed_out = True
                exit_code = -1
                try:
                    container.kill()
                except Exception:  # noqa: BLE001 - best effort
                    pass

            # NOTE: docker-py's `.logs()` interleaves stdout/stderr into a
            # single stream by default. `demux=True` gives real separation
            # (a tuple of (stdout_bytes, stderr_bytes)) at the cost of a
            # slightly different return shape, which is what we use here so
            # ExecResult.stderr is genuinely populated rather than always
            # empty.
            try:
                stdout_bytes, stderr_bytes = container.logs(stdout=True, stderr=True, demux=True)
            except Exception:  # noqa: BLE001 - container may already be gone after a kill
                stdout_bytes, stderr_bytes = b"", b""
            stdout = (stdout_bytes or b"").decode("utf-8", errors="replace")
            stderr = (stderr_bytes or b"").decode("utf-8", errors="replace")

            return ExecResult(
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_seconds=time.perf_counter() - started,
                timed_out=timed_out,
            )
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:  # noqa: BLE001 - best effort cleanup
                    pass
                sandbox.container_id = None

    # ------------------------------------------------------------------
    # Local subprocess execution (fallback; this is what actually runs here)
    # ------------------------------------------------------------------
    async def _execute_subprocess(self, sandbox: _Sandbox, command: str, timeout: int) -> ExecResult:
        """Run ``command`` as a restricted host subprocess.

        Best-effort isolation only: a trimmed environment plus (on POSIX,
        where supported) CPU-time and address-space rlimits applied in the
        child before exec. This does **not** provide filesystem or network
        isolation -- it is a resource-limited subprocess on the same
        kernel as the host, not a security boundary. Use docker mode when a
        real sandbox is required.
        """
        env = {key: os.environ[key] for key in _ALLOWED_ENV_KEYS if key in os.environ}
        sandbox.workdir.mkdir(parents=True, exist_ok=True)

        started = time.perf_counter()
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=str(sandbox.workdir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            preexec_fn=self._child_preexec if os.name == "posix" else None,
            start_new_session=True,  # own process group, so we can kill the whole tree on timeout
        )

        timed_out = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            exit_code = process.returncode if process.returncode is not None else -1
        except asyncio.TimeoutError:
            timed_out = True
            exit_code = -1
            stdout_bytes, stderr_bytes = b"", b""
            await self._kill_process_group(process)
            # Drain whatever partial output is available without blocking further.
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=2)
            except Exception:  # noqa: BLE001 - best effort partial-output capture
                pass

        return ExecResult(
            stdout=(stdout_bytes or b"").decode("utf-8", errors="replace"),
            stderr=(stderr_bytes or b"").decode("utf-8", errors="replace"),
            exit_code=exit_code,
            duration_seconds=time.perf_counter() - started,
            timed_out=timed_out,
        )

    def _child_preexec(self) -> None:
        """Runs in the forked child before exec. Best-effort resource limits.

        Wrapped so that platforms/containers which reject ``setrlimit``
        (common in already-sandboxed CI runners) never crash command
        execution -- we simply proceed without that particular limit.
        """
        cpu_seconds = max(1, int(self.settings.sandbox_timeout_seconds))
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        except (ValueError, OSError):
            pass
        try:
            mem_bytes = self.settings.sandbox_memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        except (ValueError, OSError):
            pass

    @staticmethod
    async def _kill_process_group(process: asyncio.subprocess.Process) -> None:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.kill()
            except ProcessLookupError:
                pass
        try:
            await process.wait()
        except Exception:  # noqa: BLE001 - best effort
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _require_sandbox(self, sandbox_id: str) -> _Sandbox:
        sandbox = self._sandboxes.get(sandbox_id)
        if sandbox is None:
            raise KeyError(f"Unknown sandbox_id: {sandbox_id}")
        return sandbox

    def workdir_for(self, sandbox_id: str) -> Path:
        """Return the on-disk path backing a sandbox (useful for tests/tools)."""
        return self._require_sandbox(sandbox_id).workdir
