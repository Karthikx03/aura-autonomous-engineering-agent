"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { type TaskState, getTask, getTaskTests } from "@/lib/api";
import { sampleTasks, sampleTestReport } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import StatTile from "@/components/StatTile";
import SampleDataBadge from "@/components/SampleDataBadge";
import TaskStatusBadge from "@/components/TaskStatusBadge";
import type { TestReport } from "@/lib/api";

export default function TestsPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId ?? "";

  const [task, setTask] = useState<TaskState | null>(null);
  const [report, setReport] = useState<TestReport | null>(null);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;

    async function load() {
      try {
        const taskResp = await getTask(taskId);
        if (cancelled) return;
        setTask(taskResp);
        try {
          const testResp = await getTaskTests(taskId);
          if (!cancelled) setReport(testResp);
        } catch {
          if (!cancelled) setReport(taskResp.final_test_report);
        }
        setUsingSampleData(false);
      } catch {
        if (cancelled) return;
        const fallback = sampleTasks.find((t) => t.task_id === taskId) ?? sampleTasks[0];
        setTask(fallback);
        setReport(fallback.final_test_report ?? sampleTestReport);
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
        <p className="text-[12.5px] text-text-faint">Loading test report…</p>
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

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-text">Tests</h1>
            <TaskStatusBadge status={task.status} />
          </div>
          <p className="mt-0.5 text-[11.5px] text-text-faint">
            {task.task_id} · {task.goal}
          </p>
        </div>
        {usingSampleData && <SampleDataBadge />}
      </div>

      {!report ? (
        <Panel>
          <p className="text-[12px] text-text-faint">
            No final test report available for this task yet.
          </p>
        </Panel>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <StatTile label="Total" value={report.total} />
            <StatTile label="Passed" value={report.passed} accent />
            <StatTile label="Failed" value={report.failed} />
            <StatTile label="Skipped" value={report.skipped} />
            <StatTile label="Coverage" value={`${report.coverage_percent.toFixed(1)}%`} />
          </div>

          <Panel title={`Failures (${report.failures.length})`}>
            {report.failures.length === 0 ? (
              <p className="text-[12px] text-success">All tests passed — no failures.</p>
            ) : (
              <ul className="flex flex-col divide-y divide-border">
                {report.failures.map((f, idx) => (
                  <li key={idx} className="py-2.5 first:pt-0 last:pb-0">
                    <p className="font-mono text-[12px] text-danger">{f.name}</p>
                    <p className="mt-0.5 text-[11.5px] text-text-dim">{f.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Raw Output">
            <pre className="scrollbar-thin max-h-72 overflow-auto whitespace-pre-wrap rounded border border-border bg-bg p-3 font-mono text-[11px] text-text-dim">
              {report.raw_output || "—"}
            </pre>
          </Panel>

          <p className="text-[11px] text-text-faint">
            Duration: {report.duration_seconds.toFixed(2)}s
          </p>
        </>
      )}
    </div>
  );
}
