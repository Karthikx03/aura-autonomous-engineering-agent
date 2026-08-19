# Development Workflow

AURA was built in phases, moving from foundational config outward to
agents, orchestration, sandboxing, the API/UI, and finally the benchmark
and demo. This page is a high-level reference for that phased structure
and day-to-day dev commands — see `CONTRIBUTING.md` for the PR process
itself.

## Phase-by-phase reference

1. **Project scaffolding** — repo layout, `backend/app/config.py`
   (`Settings`), dependency manifests.
2. **LLM abstraction** — `LLMProvider` base interface
   (`app/llm/base.py`), `MockProvider` first (so everything downstream is
   testable without API keys), then OpenAI/Anthropic/Gemini/Ollama.
3. **Tool system** — `Tool`/`ToolRegistry` base (`app/tools/base.py`),
   file tools with root-bound path resolution, command/test tools, git
   tools.
4. **Shared state schemas** — `PlanResult`, `RepoMap`, `CodeChange`,
   `TestReport`, `DebugReport`, `SecurityIssue`, `SecurityReport`,
   `TaskState` (`app/orchestrator/state.py`).
5. **Planner agent** — goal → `PlanResult`.
6. **RepositoryAnalyst agent** — filesystem-driven `RepoMap`.
7. **Coder agent** — plan → structured edits, applied via tools only.
8. **Sandbox manager** — Docker-mode container execution plus the
   local-subprocess fallback, resource limits, timeouts.
9. **Tester agent** — runs the suite through the sandbox, parses results
   into `TestReport`.
10. **Debugger agent** — failing `TestReport` → `DebugReport`, feeding back
    into another Coder pass.
11. **Security agent** — deterministic regex rule set → `SecurityReport`.
12. **Orchestrator** — wires all six agents into the bounded autonomous
    loop, emits `AgentEvent`s at every step.
13. **Git integration** — `GitManager` (status/diff/log/commit) used by
    tools and by the Orchestrator's commit step.
14. **Persistent memory** — SQLAlchemy models for durable task history,
    independent of the in-process `TaskState`.
15. **WebSocket + REST API** — `ConnectionManager`, `AgentEvent`
    broadcasting, and the `/api/*` routes documented in `docs/api.md`.
16. **Frontend** — Next.js dashboard consuming the REST/WebSocket API, with
    graceful fallback to sample data when the backend is unreachable.
17. **AURA-Bench + demo mode** — the 20-task benchmark with its
    `--validate` harness proof, and the offline `scripts/run_demo.sh` walk
    through analyze → test (fail) → fix → test (pass) → report.

## Module ownership map

| Area | Owner scope |
|---|---|
| `backend/app/**` | Backend engineer(s) — FastAPI app, agents, orchestrator, sandbox, git integration, memory, websocket, API |
| `frontend/**` | Frontend engineer(s) — Next.js app |
| `aura-bench/**`, `demo/**` | Benchmark/demo engineer(s) |
| `README.md`, `ARCHITECTURE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `LICENSE`, `docs/*.md`, `.env.example`, `.gitignore`, `docker-compose.yml`, `docker/*`, `.github/workflows/ci.yml` | Docs/infra owner(s) |

## Linting and testing commands

```bash
# Backend
cd backend
ruff check app                 # lint
pytest                         # unit/integration tests
pytest --cov=app                # with coverage

# Frontend
cd frontend
npm run lint
npm run build
npm test                        # if/when a test script is configured

# AURA-Bench
python3 aura-bench/runner/runner.py --validate
```

These are exactly the jobs CI runs (`.github/workflows/ci.yml`):
`backend-lint`, `backend-test`, `frontend-build`, `bench-validate`.

## Design principles carried through every phase

- **No fabrication.** Docs, READMEs, and PR descriptions describe only what
  is actually implemented and tested; unfinished capabilities go in the
  Roadmap, not the feature list.
- **Zero-key runnable.** `MockProvider` and the demo script mean the whole
  loop — planning, coding, testing, debugging, security scanning — is
  exercisable and CI-verifiable without any real LLM credentials.
- **Tools, not raw execution.** Agents never touch the filesystem or a
  shell directly; every interaction goes through the logged, root-bound
  Tool System.
- **Honest about isolation.** The sandbox's Docker-vs-fallback distinction
  is surfaced everywhere it matters (`SandboxManager.mode`,
  `SECURITY.md`, `docs/sandbox.md`) rather than glossed over.
