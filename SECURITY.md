# Security

AURA executes LLM-generated code changes and runs shell commands on behalf
of an autonomous agent loop. That is an inherently higher-risk surface than
a typical web app, so this document is written to be read, not skimmed —
especially the sandbox section.

## Threat model summary

AURA's main risk is **AI-generated or AI-selected code and commands running
with more trust than they've earned**. The mitigations below are organized
around that: bound what agents can touch, isolate what they execute, and
scan what they produce — while being explicit about where those mitigations
are strong versus best-effort.

## No secrets in the repository

- `.env` is git-ignored; only `.env.example` (with placeholder values) is
  committed. See `.gitignore` and `.env.example`.
- API keys for LLM providers (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
  `GOOGLE_API_KEY`) are read from environment variables only, never
  hard-coded.
- The local-subprocess sandbox fallback deliberately passes a **trimmed
  environment** (`PATH`, `HOME`, `LANG` only) to commands it runs, so host
  secrets sitting in the parent process's environment are not implicitly
  handed to agent-run commands.

## Sandbox isolation — read this before running untrusted code

`SandboxManager` (`backend/app/sandbox/sandbox_manager.py`) is the
component responsible for isolating command execution (test runs, agent
commands, etc.) from the host. It has **two modes**, and the difference
between them matters:

### Docker mode (`mode == "docker"`) — the intended isolation boundary

Used automatically whenever a Docker daemon is reachable at startup. Each
command runs in its own `python:3.12-slim` container with:

- a memory limit (`SANDBOX_MEMORY_LIMIT_MB`)
- a CPU limit (`SANDBOX_CPU_LIMIT`, expressed as nano-CPUs)
- networking disabled by default (`SANDBOX_NETWORK_DISABLED=true`)
- a hard wall-clock timeout (`SANDBOX_TIMEOUT_SECONDS`), after which the
  container is killed
- its own filesystem, mounted only from the copied sandbox workdir, and
  removed after the run

This is a real containment boundary and is the mode AURA is designed to run
untrusted, agent-generated code under.

### Local-subprocess fallback (`mode == "local-subprocess"`) — reduced guarantees, read carefully

When no Docker daemon is reachable (for example: a dev machine without
Docker running, or a container environment that ships the Docker CLI but
has no accessible `dockerd`), `SandboxManager` **transparently falls back**
to running the command as a plain OS subprocess:

- it runs in its own temp working directory and its own process group (so
  it can be killed as a tree on timeout)
- it gets a trimmed environment and best-effort `RLIMIT_CPU` /
  `RLIMIT_AS` resource limits where the platform supports `setrlimit`
- it is still bounded by `SANDBOX_TIMEOUT_SECONDS`

**This is explicitly not an equivalent security boundary.** The subprocess
runs as the same OS user, in the same kernel, with the same filesystem
visibility as the host AURA process. There is no filesystem isolation, no
network isolation, and no cgroup-enforced resource ceiling — only
best-effort rlimits that some platforms silently ignore. `SandboxManager`
exposes `.mode` publicly precisely so this distinction is never hidden from
callers, logs, or the UI.

**Practical guidance:** local-subprocess mode is acceptable for running your
own trusted code during local development (e.g. this repo's own test
suite). It is **not recommended** for executing code you would not
otherwise run directly on your machine. If you intend to point AURA at
untrusted repositories or fully autonomous, unreviewed code generation,
run it with a reachable Docker daemon so `mode == "docker"` is active —
`docker-compose.yml` mounts the host Docker socket into the backend
container for this reason.

## Filesystem access is bound and traversal-checked

Every file-touching tool (`read_file`, `write_file`, `edit_file`,
`list_directory`, `search_code`) is constructed with a bound `root`
directory and resolves every path argument against it
(`resolve_in_root()` in `backend/app/tools/file_tools.py`). A path that
would escape that root — via `..` traversal or an absolute path pointing
elsewhere — is rejected with an error before any I/O happens. This is a
real, tested boundary, not a UI-level convenience check.

## Tools are the only sanctioned execution path

Agents never call `eval`, `exec`, or a raw shell directly against their own
output. Every filesystem or shell interaction an agent performs goes
through the `Tool` / `ToolRegistry` abstraction (`backend/app/tools/`),
and every tool call is logged (agent, tool name, target path, status,
duration) via the observability logger. Command and test execution tools
route through `SandboxManager`, so the isolation guarantees (and caveats)
above apply to them.

## SecurityAgent: static analysis, not a guarantee

`SecurityAgent` (`backend/app/agents/security.py`) runs a deterministic,
regex-based scan over changed source files — no LLM call, no network
access, fully reproducible. It currently flags:

- hardcoded secrets / credentials (`api_key = "..."`-shaped literals)
- AWS access key literals (`AKIA...`)
- `eval(` / `exec(` usage
- `os.system(...)` and `subprocess.*(..., shell=True)`
- unsafe deserialization (`pickle.loads(...)`)
- `yaml.load()` without `SafeLoader`
- disabled TLS certificate verification (`verify=False`)
- naive SQL string interpolation in query-shaped strings
- path-traversal literals (`../../`)

High/critical findings are counted against `SECURITY_MAX_FINDINGS_BEFORE_BLOCK`
and can block the Orchestrator's auto-commit step. This is intentionally a
**heuristic linter**, not a formal guarantee of safety: it will miss issues
outside its rule set and can produce false positives. It should be treated
as one signal among several (code review, tests, the sandbox boundary
above), not as a certification that generated code is safe to run
unsandboxed.

## Not yet implemented

Being direct about gaps, per this project's own no-fabrication policy:

- **Dependency vulnerability scanning** (e.g. scanning `requirements.txt` /
  `package.json` against a CVE database) is **not implemented**. This is a
  roadmap item, not a current feature — see the Roadmap in `README.md`.
- Static analysis is limited to the rule set above; there is no data-flow or
  taint analysis, and no third-party SAST tool is integrated yet.

## Reporting a vulnerability

There is no dedicated security inbox for this project yet. If you find a
vulnerability, please **open a GitHub Security Advisory on this
repository** (Security tab → "Report a vulnerability") rather than a public
issue, so it can be triaged privately before any public disclosure.
