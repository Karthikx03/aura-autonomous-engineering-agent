# API Reference

The backend (`backend/app/main.py`, `backend/app/api/`) exposes a REST API
plus a WebSocket endpoint for live task events. All REST responses are
JSON. This page documents the designed API surface; `backend/app` is
developed alongside these docs, so treat this as the contract the backend
is built against (exercised in `backend/tests/test_api.py`) rather than a
guarantee that every route is finished in any given commit — check that
test file or run the backend yourself if you need to confirm current
status.

Base URL (local dev): `http://localhost:8000`

## REST endpoints

### `GET /`

Health check.

```json
{"status": "ok", "service": "AURA"}
```

### `GET /api/providers`

Lists which LLM providers are wired up and which is the configured default.

```json
{"available": ["anthropic", "gemini", "google", "mock", "ollama", "openai"], "default": "mock"}
```

### `POST /api/tasks`

Starts a new autonomous task. Responds immediately with a `task_id` — the
orchestrator run happens in the background; subscribe to
`/ws/tasks/{task_id}` or poll `GET /api/tasks/{id}` for progress.

**Request body:**

```json
{
  "goal": "Add input validation to the signup endpoint",
  "repo_path": "/absolute/path/to/target/repo",
  "provider": "mock"
}
```

- `goal` (string, required) — natural-language description of the task.
- `repo_path` (string, required) — absolute path to the target repository.
- `provider` (string, optional) — one of the values from `GET
  /api/providers`; defaults to the server's `DEFAULT_LLM_PROVIDER`.

**Response:**

```json
{"task_id": "a1b2c3d4e5f6"}
```

### `GET /api/tasks`

Lists known tasks (summary view).

### `GET /api/tasks/{id}`

Returns the current `TaskState` for a task (see schema below). `404` if
`id` is unknown.

### `GET /api/tasks/{id}/events`

Returns the accumulated `AgentEvent` history for a task (the same events
streamed live over the WebSocket). `404` if `id` is unknown.

### `GET /api/tasks/{id}/tests`

Returns the task's latest `TestReport`.

### `GET /api/tasks/{id}/security`

Returns the task's `SecurityReport`.

### `GET /api/metrics`

Returns process/orchestrator metrics (e.g. `tool_calls_total`), gated by
`METRICS_ENABLED`. Intended to also be scrapeable by Prometheus when the
`observability` Docker Compose profile is enabled.

## WebSocket: `/ws/tasks/{id}`

Subscribes the connection to live `AgentEvent`s for task `id`. Every
message is a JSON-encoded `AgentEvent`:

```json
{
  "type": "tests_failed",
  "agent": "orchestrator",
  "message": "Tests failed",
  "task_id": "a1b2c3d4e5f6",
  "data": {"iteration": 1, "failed": 3},
  "timestamp": 1755590400.123
}
```

### `AgentEvent` schema (`backend/app/websocket/events.py`)

| Field | Type | Notes |
|---|---|---|
| `type` | `EventType` (string enum) | See below |
| `agent` | `string` | Which agent/component emitted it, e.g. `"orchestrator"`, `"planner"`, `"coder"` |
| `message` | `string` | Short, human-readable summary — **never raw chain-of-thought** |
| `task_id` | `string \| null` | Task this event belongs to |
| `data` | `object` | Event-specific structured payload (e.g. `{"tasks": 4}` on planning completion) |
| `timestamp` | `float` | Unix epoch seconds |

### `EventType` values

`task_started`, `planner_started`, `planner_completed`,
`repo_analysis_started`, `repo_analysis_completed`, `coder_started`,
`file_modified`, `coder_completed`, `command_executed`, `tests_started`,
`tests_passed`, `tests_failed`, `debugger_started`, `debugger_completed`,
`fix_applied`, `security_scan_started`, `security_scan_completed`,
`git_diff_ready`, `git_commit_created`, `iteration_completed`,
`task_completed`, `task_failed`.

## `TaskState` (returned by `GET /api/tasks/{id}`)

Defined in `backend/app/orchestrator/state.py`:

| Field | Type |
|---|---|
| `task_id` | `string` |
| `goal` | `string` |
| `repo_path` | `string` |
| `status` | one of `pending, planning, analyzing, implementing, testing, debugging, security_check, verifying, committing, succeeded, failed` |
| `max_iterations` | `int` |
| `iteration` | `int` |
| `plan` | `PlanResult \| null` |
| `repo_map` | `RepoMap \| null` |
| `history` | `IterationRecord[]` |
| `security_report` | `SecurityReport \| null` |
| `final_test_report` | `TestReport \| null` |
| `commit_sha` | `string \| null` |
| `started_at` / `finished_at` | `float` (unix epoch) |
| `error` | `string \| null` |

See `docs/agents.md` for the full field lists of `PlanResult`, `RepoMap`,
`CodeChange`, `TestReport`, `DebugReport`, `SecurityIssue`, and
`SecurityReport`.
