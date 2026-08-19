"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { type AgentEvent, type TaskState, getTask, getTaskEvents } from "@/lib/api";
import { useTaskSocket } from "@/lib/useTaskSocket";
import { computeAgentStatuses } from "@/lib/agentStatus";
import { sampleEvents, sampleTasks } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import TaskStatusBadge from "@/components/TaskStatusBadge";
import SampleDataBadge from "@/components/SampleDataBadge";

function eventKey(e: AgentEvent, idx: number): string {
  return `${e.timestamp}-${e.type}-${e.agent}-${idx}`;
}

function mergeEvents(seed: AgentEvent[], live: AgentEvent[]): AgentEvent[] {
  const seen = new Set<string>();
  const merged: AgentEvent[] = [];
  for (const e of [...seed, ...live]) {
    const key = `${e.timestamp}|${e.type}|${e.agent}|${e.message}`;
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(e);
  }
  merged.sort((a, b) => a.timestamp - b.timestamp);
  return merged;
}

export default function AgentWorkspacePage() {
  const params = useParams<{ taskId: string }>();
  const taskId = params?.taskId ?? "";

  const [task, setTask] = useState<TaskState | null>(null);
  const [seedEvents, setSeedEvents] = useState<AgentEvent[]>([]);
  const [usingSampleData, setUsingSampleData] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  const { events: liveEvents, status: socketStatus } = useTaskSocket(taskId || null);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;

    async function load() {
      try {
        const [taskResp, eventsResp] = await Promise.all([
          getTask(taskId),
          getTaskEvents(taskId).catch(() => [] as AgentEvent[]),
        ]);
        if (cancelled) return;
        setTask(taskResp);
        setSeedEvents(eventsResp);
        setUsingSampleData(false);
      } catch {
        if (cancelled) return;
        const fallback = sampleTasks.find((t) => t.task_id === taskId) ?? sampleTasks[0];
        setTask(fallback);
        setSeedEvents(fallback.task_id === sampleTasks[0].task_id ? sampleEvents : []);
        setUsingSampleData(true);
        setNotFound(!sampleTasks.some((t) => t.task_id === taskId));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [taskId]);

  const events = useMemo(() => mergeEvents(seedEvents, liveEvents), [seedEvents, liveEvents]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [events.length]);

  const agentRows = useMemo(
    () => (task ? computeAgentStatuses(task.status, events) : []),
    [task, events]
  );

  const fileChanges = useMemo(
    () =>
      events.filter((e) => e.type === "file_modified" || e.type === "git_diff_ready"),
    [events]
  );
  const toolCalls = useMemo(
    () => events.filter((e) => e.type === "command_executed"),
    [events]
  );

  if (!taskId) {
    return (
      <div className="mx-auto max-w-2xl p-5">
        <p className="text-[12.5px] text-text-dim">No task id in URL.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl p-5">
        <p className="text-[12.5px] text-text-faint">Loading task…</p>
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
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="truncate text-lg font-semibold text-text">{task.goal}</h1>
            <TaskStatusBadge status={task.status} />
          </div>
          <p className="mt-1 text-[11.5px] text-text-faint">
            {task.task_id} · {task.repo_path} · iteration {task.iteration}/{task.max_iterations}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {usingSampleData && <SampleDataBadge />}
          {notFound && (
            <span className="text-[11px] text-warning">
              Task id not found in sample set — showing a representative sample task instead.
            </span>
          )}
        </div>
      </div>

      {task.error && (
        <div className="rounded border border-danger/30 bg-danger/10 px-3.5 py-2.5 text-[12px] text-danger">
          {task.error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <Panel title="Agent Status" className="lg:col-span-1">
          <ul className="flex flex-col gap-2">
            {agentRows.map((row) => (
              <li
                key={row.key}
                className="flex items-center justify-between rounded border border-border px-3 py-2"
              >
                <span className="text-[12.5px] text-text">{row.label}</span>
                <AgentStateIndicator state={row.state} />
              </li>
            ))}
          </ul>
          <div className="mt-3 flex items-center gap-1.5 border-t border-border pt-3 text-[10.5px] text-text-faint">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                socketStatus === "open"
                  ? "bg-success"
                  : socketStatus === "connecting"
                    ? "bg-warning"
                    : "bg-text-faint"
              }`}
            />
            live socket: {socketStatus}
          </div>
        </Panel>

        <Panel title="Plan" className="lg:col-span-2">
          {task.plan ? (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <PlanList title="Requirements" items={task.plan.requirements} />
              <PlanList title="Tasks" items={task.plan.tasks} />
              <PlanList title="Files" items={task.plan.files} mono />
              <PlanList title="Risks" items={task.plan.risks} tone="warning" />
            </div>
          ) : (
            <p className="text-[12px] text-text-faint">
              No plan available yet — the planner has not completed for this task.
            </p>
          )}
        </Panel>
      </div>

      <Panel title="Live Event Stream">
        <div
          ref={logRef}
          className="scrollbar-thin h-72 overflow-y-auto rounded border border-border bg-bg p-3 font-mono text-[11.5px] leading-relaxed"
        >
          {events.length === 0 ? (
            <p className="text-text-faint">No events yet.</p>
          ) : (
            events.map((e, idx) => (
              <div key={eventKey(e, idx)} className="flex gap-2 whitespace-pre-wrap py-0.5">
                <span className="shrink-0 text-text-faint">
                  {new Date(e.timestamp * 1000).toLocaleTimeString()}
                </span>
                <span className="shrink-0 text-violet">[{e.agent}]</span>
                <span className="shrink-0 text-accent">{e.type}</span>
                <span className="text-text-dim">{e.message}</span>
              </div>
            ))
          )}
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Panel title={`File Changes (${fileChanges.length})`}>
          {fileChanges.length === 0 ? (
            <p className="text-[12px] text-text-faint">No file changes recorded yet.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {fileChanges.map((e, idx) => (
                <li key={eventKey(e, idx)} className="py-2 first:pt-0 last:pb-0">
                  <p className="font-mono text-[11.5px] text-text">
                    {(e.data?.file as string) ?? e.message}
                  </p>
                  <p className="text-[10.5px] text-text-faint">
                    {new Date(e.timestamp * 1000).toLocaleTimeString()} · {e.type}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title={`Tool Calls (${toolCalls.length})`}>
          {toolCalls.length === 0 ? (
            <p className="text-[12px] text-text-faint">No tool/command calls recorded yet.</p>
          ) : (
            <ul className="flex flex-col divide-y divide-border">
              {toolCalls.map((e, idx) => (
                <li key={eventKey(e, idx)} className="py-2 first:pt-0 last:pb-0">
                  <p className="font-mono text-[11.5px] text-text">
                    {(e.data?.command as string) ?? e.message}
                  </p>
                  <p className="text-[10.5px] text-text-faint">
                    {new Date(e.timestamp * 1000).toLocaleTimeString()}
                    {typeof e.data?.exit_code !== "undefined" && ` · exit ${e.data.exit_code}`}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="flex gap-3 text-[11.5px]">
        <Link href={`/execution/${task.task_id}`} className="text-accent hover:underline">
          View execution log →
        </Link>
        <Link href={`/tests/${task.task_id}`} className="text-accent hover:underline">
          View tests →
        </Link>
        <Link href={`/security/${task.task_id}`} className="text-accent hover:underline">
          View security report →
        </Link>
      </div>
    </div>
  );
}

function AgentStateIndicator({ state }: { state: "done" | "active" | "pending" }) {
  if (state === "done") {
    return <span className="text-[12px] font-medium text-success">✓ done</span>;
  }
  if (state === "active") {
    return (
      <span className="flex items-center gap-1.5 text-[12px] font-medium text-accent">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
        active
      </span>
    );
  }
  return <span className="text-[12px] text-text-faint">○ pending</span>;
}

function PlanList({
  title,
  items,
  mono = false,
  tone,
}: {
  title: string;
  items: string[];
  mono?: boolean;
  tone?: "warning";
}) {
  return (
    <div>
      <h3 className="mb-1.5 text-[10.5px] uppercase tracking-wide text-text-faint">{title}</h3>
      {items.length === 0 ? (
        <p className="text-[11.5px] text-text-faint">—</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {items.map((item, idx) => (
            <li
              key={idx}
              className={`text-[11.5px] leading-snug ${mono ? "font-mono" : ""} ${
                tone === "warning" ? "text-warning" : "text-text-dim"
              }`}
            >
              · {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
