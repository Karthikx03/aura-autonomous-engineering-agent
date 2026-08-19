# AURA Architecture

This document describes the actual module layout of AURA as implemented under
`backend/app/` and `frontend/`, the autonomous execution loop the
Orchestrator drives, and how the pieces talk to each other. Every component
described here corresponds to a real module in the codebase — nothing in
this document describes aspirational or unimplemented behavior (see the
Roadmap in [README.md](README.md) for what's intentionally out of scope
today).

## 1. System architecture

```mermaid
flowchart TB
    subgraph Client
        UI["Next.js UI<br/>(Dashboard, Workspace, Code, Execution, Tests, Security, History)"]
    end

    subgraph Backend["FastAPI backend (backend/app)"]
        API["API Gateway<br/>REST + WebSocket (app/api, app/main.py)"]
        ORCH["Orchestrator<br/>(app/orchestrator)"]

        subgraph Agents["Specialized agents (app/agents)"]
            PLANNER["Planner"]
            ANALYST["RepositoryAnalyst"]
            CODER["Coder"]
            DEBUGGER["Debugger"]
            TESTER["Tester"]
            SECURITY["Security<br/>(deterministic static analysis)"]
        end

        TOOLS["Tool System<br/>(app/tools)<br/>read_file / write_file / edit_file /<br/>list_directory / search_code / run_command /<br/>run_tests / git_status / git_diff / git_log / git_commit"]
        SANDBOX["Sandbox Manager<br/>(app/sandbox)"]
        GIT["Git Integration<br/>(app/git_integration, GitPython)"]
        MEMORY["Persistent Memory<br/>(app/memory, SQLAlchemy:<br/>SQLite dev/test, PostgreSQL in docker-compose)"]
        LLM["LLM Abstraction<br/>(app/llm: OpenAI, Anthropic, Gemini,<br/>Ollama, MockProvider)"]
        OBS["Observability<br/>(app/observability: structured logging,<br/>Prometheus metrics)"]
    end

    UI -- "REST calls" --> API
    UI <-- "WebSocket events<br/>(AgentEvent stream)" --> API
    API --> ORCH
    ORCH --> PLANNER
    ORCH --> ANALYST
    ORCH --> CODER
    ORCH --> DEBUGGER
    ORCH --> TESTER
    ORCH --> SECURITY
    PLANNER --> LLM
    CODER --> LLM
    DEBUGGER --> LLM
    ANALYST --> LLM

    PLANNER -.-> TOOLS
    ANALYST --> TOOLS
    CODER --> TOOLS
    DEBUGGER -.-> TOOLS
    TESTER --> TOOLS
    SECURITY -.-> TOOLS

    TOOLS --> SANDBOX
    TOOLS --> GIT
    ORCH --> MEMORY
    ORCH --> OBS
    ORCH --> GIT
```

Notes on the diagram:

- `Planner` and `Debugger` reason via the LLM and mostly do not need the Tool
  System directly (dotted edges); `RepositoryAnalyst`, `Coder`, `Tester`, and
  `Security` walk the filesystem, apply edits, and run commands through it.
- The **Tool System** is the only sanctioned way an agent touches the
  filesystem or a shell — there is no raw `eval`/`exec` path for agent
  output. File tools are bound to a sandbox root and reject path escapes;
  command/test tools execute through the **Sandbox Manager**.
- The **Sandbox Manager** runs commands in a real Docker container when a
  daemon is reachable, and transparently falls back to a reduced-isolation
  local-subprocess mode otherwise (see §4 and `SECURITY.md`).

## 2. Component descriptions

- **API Gateway (`app/api/`, `app/main.py`)** — FastAPI app exposing REST
  endpoints for tasks, providers, tests, security reports, and metrics, plus
  a `/ws/tasks/{id}` WebSocket for live agent event streaming. See
  [docs/api.md](docs/api.md) for the full endpoint reference.
- **Orchestrator (`app/orchestrator/`)** — Owns `TaskState` and drives the
  autonomous loop: plan → analyze → (implement → test → debug/fix)\* →
  security → verify → commit → report. Bounded by `max_iterations` (default
  5, configurable via `MAX_ITERATIONS`) — there is no infinite retry.
- **LLM abstraction (`app/llm/`)** — A single `LLMProvider` interface with
  concrete implementations for OpenAI, Anthropic, Gemini, and Ollama, plus a
  deterministic, offline `MockProvider`. `app/llm/factory.py` selects a
  provider by name and transparently falls back to `MockProvider` if the
  requested provider isn't configured (missing key) — this is what keeps
  tests, CI, and demo mode runnable with zero API keys.
- **Agents (`app/agents/`)**:
  - `PlannerAgent` — turns a natural-language goal into a `PlanResult`.
  - `RepositoryAnalystAgent` — walks the repository to build a `RepoMap`
    (languages, frameworks, dependencies, test files, git presence) computed
    from real filesystem facts, optionally topped with an LLM-generated
    summary string.
  - `CoderAgent` — asks the LLM for a structured list of edits and applies
    them through the Tool System (`write_file` / `edit_file`), never by
    overwriting the repo wholesale.
  - `TesterAgent` — runs the project's test suite via the `run_tests` tool
    and returns a `TestReport`.
  - `DebuggerAgent` — given a failing `TestReport`, proposes a `DebugReport`
    (root cause, affected files, proposed fix, confidence).
  - `SecurityAgent` — deterministic regex-based static analysis (no LLM
    call) producing a `SecurityReport`.
- **Tool System (`app/tools/`)** — `Tool` base class + `ToolRegistry`. Every
  invocation is logged (agent, tool, target path, status, duration). File
  tools resolve every path against a bound root and reject traversal.
- **Sandbox (`app/sandbox/`)** — `SandboxManager`, described in §4.
- **Git integration (`app/git_integration/`)** — `GitManager`, a thin
  GitPython wrapper for status/diff/log/commit, used both by the Tool
  System and directly by the Orchestrator's commit step.
- **Memory (`app/memory/`)** — SQLAlchemy 2.0 models (`Project`, `TaskRun`,
  `IterationRecordModel`, `FileChangeModel`, `AgentDecisionModel`) — the
  durable record of what a task run did, independent of the in-process
  Pydantic `TaskState`.
- **WebSocket (`app/websocket/`)** — `AgentEvent` schema and
  `ConnectionManager`, which fans out structured events to every socket
  subscribed to a task (or globally). Agents never stream raw
  chain-of-thought — only concise, structured event summaries.
- **Observability (`app/observability/`)** — structured event logging today;
  Prometheus metrics gated behind `METRICS_ENABLED`.

## 3. Agent interaction for one task run

```mermaid
sequenceDiagram
    participant UI as Next.js UI
    participant API as API Gateway
    participant ORCH as Orchestrator
    participant PLAN as Planner
    participant ANLY as RepositoryAnalyst
    participant CODE as Coder
    participant TEST as Tester
    participant DBG as Debugger
    participant SEC as Security
    participant GIT as Git Integration
    participant WS as WebSocket Manager

    UI->>API: POST /api/tasks {goal, repo_path}
    API->>ORCH: run_task(goal, repo_path)
    ORCH->>WS: TASK_STARTED
    WS-->>UI: event

    ORCH->>PLAN: plan(goal)
    PLAN-->>ORCH: PlanResult
    ORCH->>WS: PLANNER_COMPLETED

    ORCH->>ANLY: analyze(repo_path)
    ANLY-->>ORCH: RepoMap
    ORCH->>WS: REPO_ANALYSIS_COMPLETED

    loop up to max_iterations
        ORCH->>CODE: implement(plan, repo_path, debug_report?)
        CODE-->>ORCH: list[CodeChange]
        ORCH->>WS: CODER_COMPLETED

        ORCH->>TEST: run_tests(repo_path)
        TEST-->>ORCH: TestReport
        ORCH->>WS: TESTS_PASSED / TESTS_FAILED

        alt tests failed and iterations remain
            ORCH->>DBG: debug(command, output, TestReport)
            DBG-->>ORCH: DebugReport
            ORCH->>WS: DEBUGGER_COMPLETED
        else tests passed
            ORCH->>ORCH: mark succeeded, break loop
        end
    end

    ORCH->>SEC: scan(repo_path)
    SEC-->>ORCH: SecurityReport
    ORCH->>WS: SECURITY_SCAN_COMPLETED

    alt succeeded and not blocking
        ORCH->>GIT: commit(repo_path, message)
        GIT-->>ORCH: commit_sha
        ORCH->>WS: GIT_COMMIT_CREATED
    end

    ORCH->>WS: TASK_COMPLETED / TASK_FAILED
    WS-->>UI: event stream (throughout, not just at the end)
```

## 4. Execution / autonomous loop

```mermaid
flowchart TD
    START([Task received: goal + repo_path]) --> PLAN[Plan: PlannerAgent produces PlanResult]
    PLAN --> ANALYZE[Analyze: RepositoryAnalyst builds RepoMap]
    ANALYZE --> LOOP{"iteration <= max_iterations?"}

    LOOP -- yes --> IMPLEMENT[Implement: CoderAgent applies edits via Tool System]
    IMPLEMENT --> RUN[Run: TesterAgent executes test suite in Sandbox]
    RUN --> TESTCHECK{Tests passed?}

    TESTCHECK -- yes --> BREAK[Break loop: mark succeeded]
    TESTCHECK -- no --> LASTCHECK{"Last allowed iteration?"}
    LASTCHECK -- no --> DEBUG[Debug: DebuggerAgent proposes DebugReport]
    DEBUG --> FIX[Fix: proposed_fix carried into next Coder pass]
    FIX --> LOOP
    LASTCHECK -- yes --> GIVEUP[Mark failed: max_iterations exhausted]
    GIVEUP --> SECURITY

    BREAK --> SECURITY[Security: SecurityAgent static-analysis scan<br/>always runs, pass or fail]
    SECURITY --> VERIFY[Verify: attach final TestReport + SecurityReport to TaskState]
    VERIFY --> COMMITCHECK{"Succeeded AND not security-blocking?"}
    COMMITCHECK -- yes --> COMMIT[Commit: GitManager commits via git_integration]
    COMMITCHECK -- no --> SKIP[Skip commit: log reason]
    COMMIT --> REPORT[Report: TaskState finalized, TASK_COMPLETED event]
    SKIP --> REPORT2[Report: TaskState finalized, TASK_FAILED or blocked event]

    LOOP -- "no (0 iterations configured)" --> SECURITY
```

The `max_iterations` bound (default `5`, set via `MAX_ITERATIONS`) is a hard
cap enforced in code, not a soft heuristic — the loop always terminates.
Security scanning and report finalization run unconditionally, even for a
task that never got its tests passing, so every task run produces a complete
`TaskState` for the UI and memory store.

## 5. Sandbox architecture

```mermaid
flowchart TD
    REQ[Agent needs to run a command<br/>e.g. run_tests, run_command] --> SM[SandboxManager]
    SM --> PROBE{"Docker daemon reachable?<br/>(client.ping() at startup)"}

    PROBE -- yes --> DMODE["mode = 'docker'"]
    DMODE --> DRUN["Run in real container:<br/>python:3.12-slim image, own filesystem,<br/>mem_limit, nano_cpus, network_disabled,<br/>killed + removed after timeout"]
    DRUN --> DRESULT["ExecResult: stdout, stderr, exit_code, timed_out"]

    PROBE -- no --> LMODE["mode = 'local-subprocess'<br/>(fallback, NOT an equivalent security boundary)"]
    LMODE --> LRUN["Run as host OS subprocess:<br/>own temp workdir + process group,<br/>trimmed env (PATH/HOME/LANG only),<br/>best-effort RLIMIT_CPU / RLIMIT_AS,<br/>hard wall-clock timeout + process-group kill"]
    LRUN --> LRESULT["ExecResult: stdout, stderr, exit_code, timed_out"]

    DRESULT --> DONE[Result returned to calling tool/agent]
    LRESULT --> DONE
```

`SandboxManager.mode` is a public attribute specifically so callers (and the
UI, and this documentation) can surface which mode is actually active — see
[docs/sandbox.md](docs/sandbox.md) and `SECURITY.md` for the full honesty
statement about what the fallback mode does and does not guarantee.

## 6. Data flow

```mermaid
flowchart LR
    REQ["Task request<br/>(REST: POST /api/tasks)"] --> ORCH[Orchestrator run_task]
    ORCH --> STATE["In-memory TaskState<br/>(pydantic, one run)"]
    STATE --> DB[("Persistent memory<br/>SQLite / PostgreSQL<br/>Project, TaskRun, IterationRecord,<br/>FileChange, AgentDecision")]
    ORCH --> EVENTS["AgentEvent stream<br/>(type, agent, message, task_id, data, timestamp)"]
    EVENTS --> WSM[WebSocket ConnectionManager]
    WSM --> UI["Next.js UI<br/>(live-updating Dashboard / Workspace / Execution / Tests / Security)"]
    DB -->|"GET /api/tasks/{id}, /tests, /security"| API[API Gateway]
    API --> UI
```

Structured events flow to the UI in real time over WebSocket as the
Orchestrator progresses; the same task's durable summary (status, iteration
count, test/security outcomes) is persisted to the memory store so the REST
endpoints can serve it after the fact, including after a backend restart.
