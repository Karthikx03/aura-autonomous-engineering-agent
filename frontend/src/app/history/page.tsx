"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { type TaskState, listTasks } from "@/lib/api";
import { sampleTasks } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import TaskStatusBadge from "@/components/TaskStatusBadge";
import SampleDataBadge from "@/components/SampleDataBadge";

function durationLabel(task: TaskState): string {
  if (!task.started_at) return "—";
  const start = new Date(task.started_at).getTime();
  const end = task.finished_at ? new Date(task.finished_at).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return "—";
  const seconds = Math.max(0, Math.round((end - start) / 1000));
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${minutes}m ${rem}s`;
}

export default function HistoryPage() {
  const [tasks, setTasks] = useState<TaskState[]>([]);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    listTasks()
      .then((t) => {
        if (cancelled) return;
        setTasks(t);
        setUsingSampleData(false);
      })
      .catch(() => {
        if (cancelled) return;
        setTasks(sampleTasks);
        setUsingSampleData(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text">History</h1>
          <p className="mt-0.5 text-[12px] text-text-dim">All tasks run by the AURA agent.</p>
        </div>
        {usingSampleData && <SampleDataBadge />}
      </div>

      <Panel>
        {loading ? (
          <p className="text-[12px] text-text-faint">Loading tasks…</p>
        ) : tasks.length === 0 ? (
          <p className="text-[12px] text-text-faint">No tasks recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-border text-left text-[10.5px] uppercase tracking-wide text-text-faint">
                  <th className="py-2 pr-3">Goal</th>
                  <th className="py-2 pr-3">Repo</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Iterations</th>
                  <th className="py-2 pr-3">Duration</th>
                  <th className="py-2 pr-3">Started</th>
                  <th className="py-2 pr-3" />
                </tr>
              </thead>
              <tbody>
                {tasks.map((task) => (
                  <tr key={task.task_id} className="border-b border-border/60 align-top">
                    <td className="max-w-[280px] py-2.5 pr-3 text-text">{task.goal}</td>
                    <td className="py-2.5 pr-3 font-mono text-text-dim">{task.repo_path}</td>
                    <td className="py-2.5 pr-3">
                      <TaskStatusBadge status={task.status} />
                    </td>
                    <td className="py-2.5 pr-3 text-text-dim">
                      {task.iteration}/{task.max_iterations}
                    </td>
                    <td className="py-2.5 pr-3 text-text-dim">{durationLabel(task)}</td>
                    <td className="py-2.5 pr-3 text-text-faint">
                      {task.started_at ? new Date(task.started_at).toLocaleString() : "—"}
                    </td>
                    <td className="py-2.5 pr-3">
                      <Link
                        href={`/agent-workspace/${task.task_id}`}
                        className="text-accent hover:underline"
                      >
                        Open →
                      </Link>
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
