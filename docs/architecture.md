# Architecture (summary)

The full architecture write-up, including all Mermaid diagrams (system
architecture, agent interaction sequence, execution loop, sandbox
architecture, and data flow), lives in [`ARCHITECTURE.md`](../ARCHITECTURE.md)
at the repository root. This page is a short pointer plus a file-path
reference table for navigating the actual code.

## Module → file-path reference

| Module | Path | Responsibility |
|---|---|---|
| API Gateway | `backend/app/api/`, `backend/app/main.py` | REST + WebSocket endpoints |
| Orchestrator | `backend/app/orchestrator/orchestrator.py` | Drives the autonomous loop, owns `TaskState` |
| Task/agent schemas | `backend/app/orchestrator/state.py` | `TaskState`, `PlanResult`, `RepoMap`, `CodeChange`, `TestReport`, `DebugReport`, `SecurityIssue`, `SecurityReport` |
| LLM abstraction | `backend/app/llm/base.py`, `factory.py` | Provider-agnostic `LLMProvider` interface + selection |
| OpenAI provider | `backend/app/llm/openai_provider.py` | OpenAI-backed `LLMProvider` |
| Anthropic provider | `backend/app/llm/anthropic_provider.py` | Anthropic-backed `LLMProvider` |
| Gemini provider | `backend/app/llm/gemini_provider.py` | Google Gemini-backed `LLMProvider` |
| Ollama provider | `backend/app/llm/ollama_provider.py` | Local Ollama-backed `LLMProvider` |
| Mock provider | `backend/app/llm/mock_provider.py` | Deterministic, offline, no-network `LLMProvider` used in tests/CI/demo |
| Planner agent | `backend/app/agents/planner.py` | Goal → `PlanResult` |
| RepositoryAnalyst agent | `backend/app/agents/repo_analyst.py` | Repo → `RepoMap` |
| Coder agent | `backend/app/agents/coder.py` | Plan (+ optional `DebugReport`) → `list[CodeChange]` |
| Debugger agent | `backend/app/agents/debugger.py` | Failing `TestReport` → `DebugReport` |
| Tester agent | `backend/app/agents/tester.py` | Repo → `TestReport` (via `run_tests` tool) |
| Security agent | `backend/app/agents/security.py` | Repo → `SecurityReport` (deterministic regex rules, no LLM) |
| Tool base + registry | `backend/app/tools/base.py`, `registry.py` | `Tool`, `ToolRegistry`, per-call logging |
| File tools | `backend/app/tools/file_tools.py` | `read_file`, `write_file`, `edit_file`, `list_directory`, `search_code` — root-bound, traversal-checked |
| Command tools | `backend/app/tools/command_tools.py` | `run_command`, `run_tests` |
| Git tools | `backend/app/tools/git_tools.py` | `git_status`, `git_diff`, `git_log`, `git_commit` |
| Sandbox | `backend/app/sandbox/sandbox_manager.py` | `SandboxManager` — Docker mode + local-subprocess fallback |
| Git integration | `backend/app/git_integration/git_manager.py` | `GitManager`, thin GitPython wrapper |
| Memory | `backend/app/memory/models.py`, `db.py` | SQLAlchemy models: `Project`, `TaskRun`, `IterationRecordModel`, `FileChangeModel`, `AgentDecisionModel` |
| WebSocket | `backend/app/websocket/events.py`, `manager.py` | `AgentEvent`, `EventType`, `ConnectionManager` |
| Observability | `backend/app/observability/logger.py` | Structured event logging (feeds Prometheus metrics when `METRICS_ENABLED=true`) |
| Config | `backend/app/config.py` | Central `Settings` (env-var driven) |
| Frontend pages | `frontend/` | Dashboard, Agent Workspace, Code (Monaco viewer), Execution, Tests, Security, History |
| AURA-Bench | `aura-bench/tasks/`, `aura-bench/runner/` | 20 micro-tasks + validator/runner |
| Demo | `demo/broken_project/`, `scripts/run_demo.sh` | Offline, zero-key demo of the full loop |

For prose descriptions of each component and the five architecture
diagrams, see [`ARCHITECTURE.md`](../ARCHITECTURE.md).
