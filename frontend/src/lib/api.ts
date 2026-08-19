/**
 * Typed API client for the AURA backend.
 *
 * The backend is a FastAPI service that may or may not be running while this
 * frontend is developed/demoed standalone. Every function here simply
 * performs a fetch and throws on failure (network error or non-2xx status);
 * callers are expected to catch and fall back to sample/demo data so the UI
 * never crashes and never silently pretends stale/fake data is live.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") || "http://localhost:8000";

export function getWsBase(): string {
  if (API_BASE.startsWith("https://")) return "wss://" + API_BASE.slice("https://".length);
  if (API_BASE.startsWith("http://")) return "ws://" + API_BASE.slice("http://".length);
  return API_BASE;
}

export function getTaskWsUrl(taskId: string): string {
  return `${getWsBase()}/ws/tasks/${encodeURIComponent(taskId)}`;
}

// ---------------------------------------------------------------------------
// Types (mirroring the backend contract)
// ---------------------------------------------------------------------------

export type TaskStatus =
  | "pending"
  | "planning"
  | "analyzing"
  | "implementing"
  | "testing"
  | "debugging"
  | "security_check"
  | "verifying"
  | "committing"
  | "succeeded"
  | "failed";

export interface Plan {
  goal: string;
  requirements: string[];
  tasks: string[];
  files: string[];
  tests: string[];
  risks: string[];
}

export interface RepoMap {
  root: string;
  languages: string[];
  frameworks: string[];
  dependencies: string[];
  test_files: string[];
  has_git: boolean;
  file_count: number;
  summary: string;
}

export interface HistoryEntry {
  iteration: number;
  summary: string;
  test_report: TestReport | null;
  debug_report: string | null;
  changes: string[];
  timestamp: string;
}

export interface TestFailure {
  name: string;
  message: string;
  [key: string]: unknown;
}

export interface TestReport {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  coverage_percent: number;
  duration_seconds: number;
  failures: TestFailure[];
  raw_output: string;
}

export interface SecurityIssue {
  rule_id: string;
  severity: "critical" | "high" | "medium" | "low" | "info" | string;
  file: string;
  line: number;
  message: string;
}

export interface SecurityReport {
  issues: SecurityIssue[];
}

export interface TaskState {
  task_id: string;
  goal: string;
  repo_path: string;
  status: TaskStatus;
  max_iterations: number;
  iteration: number;
  plan: Plan | null;
  repo_map: RepoMap | null;
  history: HistoryEntry[];
  security_report: SecurityReport | null;
  final_test_report: TestReport | null;
  commit_sha: string | null;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
}

export interface AgentEvent {
  type: string;
  agent: string;
  message: string;
  task_id: string;
  data: Record<string, unknown>;
  timestamp: number;
}

export interface ProvidersResponse {
  available: string[];
  default: string;
}

export interface CreateTaskRequest {
  goal: string;
  repo_path: string;
  provider?: string;
}

export interface CreateTaskResponse {
  task_id: string;
}

export interface MetricsResponse {
  tool_calls_total: Record<string, number>;
  tool_call_errors_total: Record<string, number>;
  agent_events_total: Record<string, number>;
  llm_calls_total: Record<string, number>;
  tasks_completed: number;
  avg_task_duration_seconds: number;
  avg_llm_latency_seconds: number;
}

// ---------------------------------------------------------------------------
// Fetch helpers
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {
      // ignore
    }
    throw new Error(`API ${path} failed: ${res.status} ${res.statusText} ${detail}`.trim());
  }
  return (await res.json()) as T;
}

export function getProviders(): Promise<ProvidersResponse> {
  return apiFetch<ProvidersResponse>("/api/providers");
}

export function createTask(body: CreateTaskRequest): Promise<CreateTaskResponse> {
  return apiFetch<CreateTaskResponse>("/api/tasks", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listTasks(): Promise<TaskState[]> {
  return apiFetch<TaskState[]>("/api/tasks");
}

export function getTask(taskId: string): Promise<TaskState> {
  return apiFetch<TaskState>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export function getTaskEvents(taskId: string): Promise<AgentEvent[]> {
  return apiFetch<AgentEvent[]>(`/api/tasks/${encodeURIComponent(taskId)}/events`);
}

export function getTaskTests(taskId: string): Promise<TestReport> {
  return apiFetch<TestReport>(`/api/tasks/${encodeURIComponent(taskId)}/tests`);
}

export function getTaskSecurity(taskId: string): Promise<SecurityReport> {
  return apiFetch<SecurityReport>(`/api/tasks/${encodeURIComponent(taskId)}/security`);
}

export function getMetrics(): Promise<MetricsResponse> {
  return apiFetch<MetricsResponse>("/api/metrics");
}
