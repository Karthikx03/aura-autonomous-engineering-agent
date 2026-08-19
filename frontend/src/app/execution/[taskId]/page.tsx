"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { type AgentEvent, type TaskState, getTask, getTaskEvents } from "@/lib/api";
import { sampleEvents, sampleTasks } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import SampleDataBadge from "@/components/SampleDataBadge";
import TaskStatusBadge from "@/components/TaskStatusBadge";

function asString(v: unknown, fallback = "—"): string {
  if (typeof v === "string" && v.length > 0) return v;
  return fallback;
}

function asNumber(v: unknown): number | null {
  return typeof v === "number" ? v : null;
}

export default function ExecutionPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId ?? "";

  const [task, setTask] = useState<TaskState | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;

    async function load() {
      try {
        const [taskResp, eventsResp] = await Promise.all([
          getTask(taskId),
          getTaskEvents(taskId),
        ]);
        if (cancelled) return;
        setTask(taskResp);
        setEvents(eventsResp);
        setUsingSampleData(false);
      } catch {
        if (cancelled) return;
        const fallback = sampleTasks.find((t) => t.task_id === taskId) ?? sampleTasks[0];
        setTask(fallback);
        setEvents(fallback.task_id === sampleTasks[0].task_id ? sampleEvents : []);
        setUsingSampleData(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl p-5">
        <p className="text-[12.5px] text-text-faint">Loading execution log…</p>
      </div>
    );
  }

  if (!task) {
    return (
      <div className="mx-auto max-w-2xl p-5">
        <p className="text-[12.5px] text-danger">Task not found.</p>
      </div>
    );
  }

  const commandEvents = events.filter((e) => e.type === "command_executed");

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-text">Execution</h1>
            <TaskStatusBadge status={task.status} />
          </div>
          <p className="mt-0.5 text-[11.5px] text-text-faint">
            {task.task_id} · {task.goal}
          </p>
        </div>
        {usingSampleData && <SampleDataBadge />}
      </div>

      <Panel title={`Executed Commands (${commandEvents.length})`}>
        {commandEvents.length === 0 ? (
          <p className="text-[12px] text-text-faint">No commands recorded for this task.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-border text-left text-[10.5px] uppercase tracking-wide text-text-faint">
                  <th className="py-2 pr-3">Time</th>
                  <th className="py-2 pr-3">Command</th>
                  <th className="py-2 pr-3">Exit</th>
                  <th className="py-2 pr-3">Duration</th>
                  <th className="py-2 pr-3">Stdout</th>
                  <th className="py-2 pr-3">Stderr</th>
                </tr>
              </thead>
              <tbody>
                {commandEvents.map((e, idx) => {
                  const exitCode = asNumber(e.data?.exit_code);
                  const duration = asNumber(e.data?.duration_seconds);
                  return (
                    <tr key={idx} className="border-b border-border/60 align-top">
                      <td className="whitespace-nowrap py-2 pr-3 text-text-faint">
                        {new Date(e.timestamp * 1000).toLocaleTimeString()}
                      </td>
                      <td className="py-2 pr-3 font-mono text-text">
                        {asString(e.data?.command, e.message)}
                      </td>
                      <td className="py-2 pr-3">
                        <span
                          className={
                            exitCode === null
                              ? "text-text-faint"
                              : exitCode === 0
                                ? "text-success"
                                : "text-danger"
                          }
                        >
                          {exitCode ?? "—"}
                        </span>
                      </td>
                      <td className="py-2 pr-3 text-text-dim">
                        {duration !== null ? `${duration.toFixed(2)}s` : "—"}
                      </td>
                      <td className="max-w-[220px] truncate py-2 pr-3 font-mono text-text-dim">
                        {asString(e.data?.stdout)}
                      </td>
                      <td className="max-w-[220px] truncate py-2 pr-3 font-mono text-danger/80">
                        {asString(e.data?.stderr)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <Panel title={`Test Runs by Iteration (${task.history.length})`}>
        {task.history.length === 0 ? (
          <p className="text-[12px] text-text-faint">No iterations recorded for this task.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-border text-left text-[10.5px] uppercase tracking-wide text-text-faint">
                  <th className="py-2 pr-3">Iter</th>
                  <th className="py-2 pr-3">Summary</th>
                  <th className="py-2 pr-3">Passed</th>
                  <th className="py-2 pr-3">Failed</th>
                  <th className="py-2 pr-3">Skipped</th>
                  <th className="py-2 pr-3">Duration</th>
                  <th className="py-2 pr-3">Files Changed</th>
                </tr>
              </thead>
              <tbody>
                {task.history.map((h) => (
                  <tr key={h.iteration} className="border-b border-border/60 align-top">
                    <td className="py-2 pr-3 text-text">{h.iteration}</td>
                    <td className="max-w-[280px] py-2 pr-3 text-text-dim">{h.summary}</td>
                    <td className="py-2 pr-3 text-success">{h.test_report?.passed ?? "—"}</td>
                    <td className="py-2 pr-3 text-danger">{h.test_report?.failed ?? "—"}</td>
                    <td className="py-2 pr-3 text-text-dim">{h.test_report?.skipped ?? "—"}</td>
                    <td className="py-2 pr-3 text-text-dim">
                      {h.test_report ? `${h.test_report.duration_seconds.toFixed(2)}s` : "—"}
                    </td>
                    <td className="py-2 pr-3 font-mono text-text-dim">
                      {h.changes.length > 0 ? h.changes.join(", ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  );
}
