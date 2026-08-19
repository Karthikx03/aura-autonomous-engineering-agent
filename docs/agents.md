# Agents

AURA has six specialized agents, each a small focused class in
`backend/app/agents/` sharing a common `BaseAgent` (`agents/base.py`, which
provides an `llm` handle, an optional `tools: ToolRegistry`, and an
`emit()` helper for structured, non-chain-of-thought event logging). Five
of the six call an LLM through the provider-agnostic `LLMProvider`
interface (`app/llm/base.py`); `SecurityAgent` does not.

All input/output schemas below are real Pydantic models defined in
`backend/app/orchestrator/state.py` unless noted otherwise.

## Planner (`agents/planner.py`)

Turns a natural-language goal (and, optionally, a `RepoMap` for context)
into a structured implementation plan. Asks the LLM for JSON and falls back
to a minimal single-task plan if the response can't be parsed, so a
malformed LLM response never crashes the run.

- **Input:** `goal: str`, `repo_map: RepoMap | None`
- **Output — `PlanResult`:**
  - `goal: str`
  - `requirements: list[str]`
  - `tasks: list[str]`
  - `files: list[str]` — file paths likely to be touched
  - `tests: list[str]` — test descriptions
  - `risks: list[str]`

## RepositoryAnalyst (`agents/repo_analyst.py`)

Builds a structural map of the target repository. The structural facts are
computed for real by walking the filesystem (extension-based language
detection, dependency/test-file discovery, git-presence check) — never
guessed by an LLM. An LLM call is used only, optionally, to produce a short
natural-language `summary` layered on top of those computed facts.

- **Input:** `repo_path: str`
- **Output — `RepoMap`:**
  - `root: str`
  - `languages: list[str]`
  - `frameworks: list[str]`
  - `dependencies: list[str]`
  - `test_files: list[str]`
  - `has_git: bool`
  - `file_count: int`
  - `summary: str`

## Coder (`agents/coder.py`)

Asks the LLM for a small, structured list of edits (`{"path", "action",
"content_or_patch"}`) and applies exactly those edits through the injected
`ToolRegistry` — `write_file` for create/overwrite, `edit_file` for a
find/replace patch. It never overwrites the repository wholesale, and the
`CodeChange` objects it returns reflect the actual tool call results, not
the LLM's unverified claims about what it did.

- **Input:** `plan: PlanResult`, `repo_path: str`, `debug_report:
  DebugReport | None` (carried in on a retry after a failed test run)
- **Output — `list[CodeChange]`**, one per applied edit:
  - `path: str`
  - `action: str` — `"created" | "modified" | "deleted"`
  - `diff_preview: str`

## Debugger (`agents/debugger.py`)

Given a failing `TestReport` (plus the command and captured stdout/stderr),
diagnoses a root cause and proposes a fix for the next Coder pass.

- **Input:** `command: str`, `stdout: str`, `stderr: str`, `test_report:
  TestReport`
- **Output — `DebugReport`:**
  - `root_cause: str`
  - `affected_files: list[str]`
  - `proposed_fix: str`
  - `confidence: float` (0.0–1.0)

## Tester (`agents/tester.py`)

Runs the repository's test suite via the `run_tests` tool (which itself
executes through the Sandbox Manager) and normalizes the result into a
`TestReport`. If no `ToolRegistry` is available, it returns an empty report
rather than raising.

- **Input:** `repo_path: str`, `test_command: str = "pytest -q"`
- **Output — `TestReport`:**
  - `total: int`, `passed: int`, `failed: int`, `skipped: int`
  - `coverage_percent: float | None`
  - `duration_seconds: float`
  - `failures: list[str]`
  - `raw_output: str`
  - `all_passed` (computed property): `True` only if `total > 0 and failed
    == 0`

## Security (`agents/security.py`)

**Deterministic static analysis — no LLM call.** Walks source files
(`.py`, `.js`, `.ts`, `.tsx`, `.jsx`) under the repository and applies a
fixed table of regex rules (hardcoded secrets, AWS key literals,
`eval`/`exec`, `os.system`/`shell=True`, unsafe deserialization, unsafe
YAML load, disabled TLS verification, naive SQL string interpolation,
path-traversal literals). See `SECURITY.md` for the full rule list and an
honest characterization of what this agent is (a heuristic linter) and
isn't (a safety guarantee).

- **Input:** `repo_path: str`
- **Output — `SecurityReport`:**
  - `issues: list[SecurityIssue]`
  - `blocking` (computed property): `True` if any issue has severity
    `"high"` or `"critical"`

  Each `SecurityIssue`:
  - `rule_id: str`
  - `severity: str` — `"low" | "medium" | "high" | "critical"`
  - `file: str`
  - `line: int | None`
  - `message: str`

## How the Orchestrator uses these

The Orchestrator (`backend/app/orchestrator/orchestrator.py`) calls these
agents in the fixed sequence plan → analyze → (implement → test → debug)\*
→ security → verify → commit, described in full in `ARCHITECTURE.md`. Each
agent's output feeds directly into the next: `PlanResult` and `RepoMap`
into `Coder`, `TestReport` into `Debugger`, and every step's completion
emits an `AgentEvent` (see `docs/api.md`) that the UI renders live.
