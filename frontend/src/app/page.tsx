"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  type MetricsResponse,
  type ProvidersResponse,
  type TaskState,
  createTask,
  getMetrics,
  getProviders,
  listTasks,
} from "@/lib/api";
import { sampleMetrics, sampleProviders, sampleTasks } from "@/lib/sampleData";
import StatTile from "@/components/StatTile";
import Panel from "@/components/Panel";
import TaskStatusBadge from "@/components/TaskStatusBadge";
import SampleDataBadge from "@/components/SampleDataBadge";

const DEMO_GOAL = "Fix the deliberately broken demo project";
const DEMO_REPO_PATH = "demo/broken_project";

export default function DashboardPage() {
  const router = useRouter();

  const [tasks, setTasks] = useState<TaskState[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [providers, setProviders] = useState<ProvidersResponse | null>(null);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [loading, setLoading] = useState(true);

  const [goal, setGoal] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [provider, setProvider] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [demoSubmitting, setDemoSubmitting] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [taskList, metricsResp, providersResp] = await Promise.all([
          listTasks(),
          getMetrics(),
          getProviders(),
        ]);
        if (cancelled) return;
        setTasks(taskList);
        setMetrics(metricsResp);
        setProviders(providersResp);
        setProvider(providersResp.default ?? providersResp.available[0] ?? "");
        setUsingSampleData(false);
      } catch {
        if (cancelled) return;
        setTasks(sampleTasks);
        setMetrics(sampleMetrics);
        setProviders(sampleProviders);
        setProvider(sampleProviders.default);
        setUsingSampleData(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const activeTasks = tasks.filter((t) =>
    ["pending", "planning", "analyzing", "implementing", "testing", "debugging", "security_check", "verifying", "committing"].includes(
      t.status
    )
  ).length;
  const completedTasks = tasks.filter((t) => t.status === "succeeded" || t.status === "failed").length;
  const succeeded = tasks.filter((t) => t.status === "succeeded").length;
  const successRate = completedTasks > 0 ? Math.round((succeeded / completedTasks) * 100) : 0;
  const iterationsList = tasks.filter((t) => t.iteration > 0).map((t) => t.iteration);
  const avgIterations =
    iterationsList.length > 0
      ? (iterationsList.reduce((a, b) => a + b, 0) / iterationsList.length).toFixed(1)
      : "0";

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!goal.trim() || !repoPath.trim()) {
      setFormError("Goal and repo path are required.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await createTask({
        goal: goal.trim(),
        repo_path: repoPath.trim(),
        provider: provider || undefined,
      });
      router.push(`/agent-workspace/${res.task_id}`);
    } catch (err) {
      setFormError(
        err instanceof Error
          ? `Failed to create task: ${err.message}`
          : "Failed to create task: unknown error."
      );
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRunDemo() {
    setDemoError(null);
    setDemoSubmitting(true);
    try {
      const res = await createTask({
        goal: DEMO_GOAL,
        repo_path: DEMO_REPO_PATH,
        provider: provider || undefined,
      });
      router.push(`/agent-workspace/${res.task_id}`);
    } catch (err) {
      setDemoError(
        err instanceof Error
          ? `Could not start demo task: ${err.message}`
          : "Could not start demo task: unknown error."
      );
    } finally {
      setDemoSubmitting(false);
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text">Dashboard</h1>
          <p className="mt-0.5 text-[12px] text-text-dim">
            Overview of AURA agent activity across all tasks.
          </p>
        </div>
        {usingSampleData && <SampleDataBadge />}
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Active Tasks" value={loading ? "…" : activeTasks} accent />
        <StatTile label="Completed Tasks" value={loading ? "…" : completedTasks} />
        <StatTile label="Success Rate" value={loading ? "…" : `${successRate}%`} />
        <StatTile label="Avg Iterations" value={loading ? "…" : avgIterations} />
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel title="New Task" className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <label className="flex flex-col gap-1.5">
              <span className="text-[11px] uppercase tracking-wide text-text-faint">Goal</span>
              <textarea
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                placeholder="e.g. Fix the failing tests in the payments module"
                rows={3}
                className="resize-none rounded border border-border bg-bg px-3 py-2 text-[12.5px] text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
              />
            </label>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <label className="flex flex-col gap-1.5">
                <span className="text-[11px] uppercase tracking-wide text-text-faint">
                  Repo Path
                </span>
                <input
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  placeholder="demo/broken_project"
                  className="rounded border border-border bg-bg px-3 py-2 text-[12.5px] text-text placeholder:text-text-faint focus:border-accent focus:outline-none"
                />
              </label>
              <label className="flex flex-col gap-1.5">
                <span className="text-[11px] uppercase tracking-wide text-text-faint">
                  Provider
                </span>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="rounded border border-border bg-bg px-3 py-2 text-[12.5px] text-text focus:border-accent focus:outline-none"
                >
                  {(providers?.available ?? []).length === 0 && (
                    <option value="">No providers available</option>
                  )}
                  {(providers?.available ?? []).map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            {formError && (
              <p className="rounded border border-danger/30 bg-danger/10 px-3 py-2 text-[12px] text-danger">
                {formError}
              </p>
            )}
            <div className="flex items-center gap-2">
              <button
                type="submit"
                disabled={submitting}
                className="rounded border border-accent/40 bg-accent/10 px-4 py-2 text-[12px] font-medium text-accent transition-colors hover:bg-accent/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Starting task…" : "Start Task"}
              </button>
              <button
                type="button"
                onClick={handleRunDemo}
                disabled={demoSubmitting}
                className="rounded border border-border px-4 py-2 text-[12px] font-medium text-text-dim transition-colors hover:border-border-strong hover:text-text disabled:cursor-not-allowed disabled:opacity-50"
              >
                {demoSubmitting ? "Launching demo…" : "Run Demo"}
              </button>
            </div>
            {demoError && (
              <p className="rounded border border-danger/30 bg-danger/10 px-3 py-2 text-[12px] text-danger">
                {demoError}
              </p>
            )}
          </form>
        </Panel>

        <Panel title="Model Usage">
          {metrics && Object.keys(metrics.llm_calls_total).length > 0 ? (
            <ul className="flex flex-col gap-2.5">
              {Object.entries(metrics.llm_calls_total)
                .sort((a, b) => b[1] - a[1])
                .map(([model, count]) => {
                  const total = Object.values(metrics.llm_calls_total).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? Math.round((count / total) * 100) : 0;
                  return (
                    <li key={model} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-[12px]">
                        <span className="text-text">{model}</span>
                        <span className="text-text-dim">
                          {count} · {pct}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-raised">
                        <div
                          className="h-full rounded-full bg-accent"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </li>
                  );
                })}
            </ul>
          ) : (
            <p className="text-[12px] text-text-faint">No model usage recorded yet.</p>
          )}
          {metrics && (
            <div className="mt-3 grid grid-cols-2 gap-2 border-t border-border pt-3 text-[11px] text-text-dim">
              <span>Tasks completed: {metrics.tasks_completed}</span>
              <span>Avg duration: {metrics.avg_task_duration_seconds.toFixed(1)}s</span>
              <span className="col-span-2">
                Avg LLM latency: {metrics.avg_llm_latency_seconds.toFixed(2)}s
              </span>
            </div>
          )}
        </Panel>
      </div>

      <Panel
        title="Recent Tasks"
        action={
          <Link href="/history" className="text-[11px] text-accent hover:underline">
            View all →
          </Link>
        }
      >
        {loading ? (
          <p className="text-[12px] text-text-faint">Loading tasks…</p>
        ) : tasks.length === 0 ? (
          <p className="text-[12px] text-text-faint">
            No tasks yet. Start one above or run the demo.
          </p>
        ) : (
          <ul className="flex flex-col divide-y divide-border">
            {tasks.slice(0, 8).map((task) => (
              <li key={task.task_id}>
                <Link
                  href={`/agent-workspace/${task.task_id}`}
                  className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0 hover:opacity-80"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12.5px] text-text">{task.goal}</p>
                    <p className="truncate text-[11px] text-text-faint">
                      {task.repo_path} · {task.task_id}
                    </p>
                  </div>
                  <TaskStatusBadge status={task.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
