# Sandbox

`SandboxManager` (`backend/app/sandbox/sandbox_manager.py`) is the
component every agent-run command (test suites, arbitrary shell commands
via the `run_command`/`run_tests` tools) executes through. This page
covers both execution modes in detail and the configuration knobs that
control them. For the security implications, read `SECURITY.md` — this
page is the "how it works," that one is the "what it does and doesn't
guarantee."

## Mode detection

On construction, `SandboxManager` probes for a live Docker daemon:

```python
import docker
client = docker.from_env()
client.ping()
```

If that succeeds, `self.mode = "docker"`. Any failure at all — daemon not
running, SDK not usable, permission denied — is treated uniformly as
"Docker unavailable" and `self.mode = "local-subprocess"`. The probe never
raises; sandbox creation always succeeds in one mode or the other.

`SandboxManager.mode` is public specifically so calling code (and the UI)
can surface which guarantee is actually in effect for a given run.

## Docker mode

Used whenever a daemon is reachable. Each `execute()` call:

1. Starts a fresh `python:3.12-slim` container with the sandbox's workdir
   bind-mounted at `/workspace`.
2. Applies `mem_limit` (from `SANDBOX_MEMORY_LIMIT_MB`), `nano_cpus` (from
   `SANDBOX_CPU_LIMIT`), and `network_disabled` (from
   `SANDBOX_NETWORK_DISABLED`).
3. Waits up to `timeout` seconds (per-call override, else
   `SANDBOX_TIMEOUT_SECONDS`); on timeout, kills the container.
4. Reads stdout/stderr back via `demux=True` (real separation, not an
   interleaved single stream).
5. Removes the container in a `finally` block, whether it succeeded, failed,
   or timed out.

This is real container isolation — its own filesystem, resource ceilings
enforced by cgroups, and no network access by default.

## Local-subprocess fallback

Used when no Docker daemon is reachable. This is the mode that actually
runs in most lightweight/headless dev containers (including the one this
project was built in, which ships the `docker` Python SDK and CLI but has
no `dockerd` running). Each `execute()` call:

1. Builds a trimmed environment containing only `PATH`, `HOME`, `LANG` from
   the host process's environment — host secrets are not implicitly passed
   through.
2. Spawns the command via `asyncio.create_subprocess_shell`, in the
   sandbox's own temp workdir, in its own process group
   (`start_new_session=True`).
3. On POSIX, applies best-effort `RLIMIT_CPU` and `RLIMIT_AS` limits in the
   child via `preexec_fn` before exec — wrapped in `try/except` so
   platforms/CI runners that reject `setrlimit` don't crash execution, they
   just proceed without that particular limit.
4. Enforces a hard wall-clock timeout (`SANDBOX_TIMEOUT_SECONDS` or a
   per-call override) via `asyncio.wait_for`; on timeout, kills the entire
   process group (`os.killpg`), not just the top-level process.

**This is best-effort resource limiting on a subprocess, not a security
sandbox.** It shares the host's kernel, filesystem, and OS user. See
`SECURITY.md` for the full statement of what this does and doesn't protect
against, and when you should insist on Docker mode instead.

## Both modes, one interface

Both code paths return the same `ExecResult`:

```python
@dataclass
class ExecResult:
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_seconds: float = 0.0
    timed_out: bool = False
```

`execute()` never raises on command failure or timeout — both are reported
through `ExecResult` so callers (agents) can inspect and react to them
programmatically rather than handling exceptions.

## Configuration knobs

All read from `backend/app/config.py` (`Settings`), settable via `.env` /
environment variables — see `.env.example`:

| Variable | Default | Meaning |
|---|---|---|
| `SANDBOX_ENABLED` | `true` | Whether tool calls route through the sandbox at all |
| `SANDBOX_CPU_LIMIT` | `1.0` | CPU limit in Docker mode (converted to `nano_cpus`) |
| `SANDBOX_MEMORY_LIMIT_MB` | `512` | Memory limit — `mem_limit` in Docker mode, `RLIMIT_AS` in fallback mode |
| `SANDBOX_TIMEOUT_SECONDS` | `60` | Wall-clock timeout for a single `execute()` call, both modes |
| `SANDBOX_NETWORK_DISABLED` | `true` | Disables container networking in Docker mode (no effect in fallback mode — see caveat above) |
| `SANDBOX_WORKDIR` | `~/.aura/sandboxes` | Root directory under which per-task sandbox workdirs are created |

## Sandbox lifecycle

- `create_sandbox(project_path)` — allocates a `sandbox_id`, creates its
  workdir under `SANDBOX_WORKDIR`, and copies `project_path` into it
  (excluding `.git`, `node_modules`, `__pycache__`, `.venv`,
  `.mypy_cache`, `.pytest_cache`).
- `copy_project(sandbox_id, project_path)` — re-syncs the workdir.
- `execute(sandbox_id, command, timeout=None)` — runs one command, as above.
- `destroy_sandbox(sandbox_id)` — removes the container (if any, Docker
  mode) and deletes the workdir.
