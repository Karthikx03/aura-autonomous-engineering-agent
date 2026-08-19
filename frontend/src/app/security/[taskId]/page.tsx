"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { type SecurityReport, type TaskState, getTask, getTaskSecurity } from "@/lib/api";
import { sampleSecurityReport, sampleTasks } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import SeverityBadge from "@/components/SeverityBadge";
import SampleDataBadge from "@/components/SampleDataBadge";
import TaskStatusBadge from "@/components/TaskStatusBadge";

const SEVERITY_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

export default function SecurityPage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId ?? "";

  const [task, setTask] = useState<TaskState | null>(null);
  const [report, setReport] = useState<SecurityReport | null>(null);
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
          const secResp = await getTaskSecurity(taskId);
          if (!cancelled) setReport(secResp);
        } catch {
          if (!cancelled) setReport(taskResp.security_report);
        }
        setUsingSampleData(false);
      } catch {
        if (cancelled) return;
        const fallback = sampleTasks.find((t) => t.task_id === taskId) ?? sampleTasks[0];
        setTask(fallback);
        setReport(fallback.security_report ?? sampleSecurityReport);
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
        <p className="text-[12.5px] text-text-faint">Loading security report…</p>
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

  const issues = [...(report?.issues ?? [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity.toLowerCase()] ?? 9) - (SEVERITY_ORDER[b.severity.toLowerCase()] ?? 9)
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 p-5">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-text">Security</h1>
            <TaskStatusBadge status={task.status} />
          </div>
          <p className="mt-0.5 text-[11.5px] text-text-faint">
            {task.task_id} · {task.goal}
          </p>
        </div>
        {usingSampleData && <SampleDataBadge />}
      </div>

      <Panel title={`Findings (${issues.length})`}>
        {issues.length === 0 ? (
          <p className="text-[12px] text-success">No security issues found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[11.5px]">
              <thead>
                <tr className="border-b border-border text-left text-[10.5px] uppercase tracking-wide text-text-faint">
                  <th className="py-2 pr-3">Severity</th>
                  <th className="py-2 pr-3">Rule</th>
                  <th className="py-2 pr-3">File</th>
                  <th className="py-2 pr-3">Line</th>
                  <th className="py-2 pr-3">Message</th>
                </tr>
              </thead>
              <tbody>
                {issues.map((issue, idx) => (
                  <tr key={idx} className="border-b border-border/60 align-top">
                    <td className="py-2 pr-3">
                      <SeverityBadge severity={issue.severity} />
                    </td>
                    <td className="py-2 pr-3 font-mono text-text-dim">{issue.rule_id}</td>
                    <td className="py-2 pr-3 font-mono text-text">{issue.file}</td>
                    <td className="py-2 pr-3 text-text-dim">{issue.line}</td>
                    <td className="py-2 pr-3 text-text-dim">{issue.message}</td>
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
