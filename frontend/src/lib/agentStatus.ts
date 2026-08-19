import type { AgentEvent, TaskStatus } from "./api";

export type AgentRunState = "done" | "active" | "pending";

export interface AgentRow {
  key: string;
  label: string;
  state: AgentRunState;
}

const STAGE_ORDER: TaskStatus[] = [
  "pending",
  "planning",
  "analyzing",
  "implementing",
  "testing",
  "debugging",
  "security_check",
  "verifying",
  "committing",
  "succeeded",
];

function stageIndex(status: TaskStatus): number {
  const idx = STAGE_ORDER.indexOf(status);
  return idx === -1 ? STAGE_ORDER.length : idx; // "failed" sorts last
}

interface AgentDef {
  key: string;
  label: string;
  startedType: string;
  completedTypes: string[];
  fallbackStages: TaskStatus[];
}

const AGENT_DEFS: AgentDef[] = [
  {
    key: "planner",
    label: "Planner",
    startedType: "planner_started",
    completedTypes: ["planner_completed"],
    fallbackStages: ["planning", "analyzing"],
  },
  {
    key: "coder",
    label: "Coder",
    startedType: "coder_started",
    completedTypes: ["coder_completed"],
    fallbackStages: ["implementing"],
  },
  {
    key: "tester",
    label: "Tester",
    startedType: "tests_started",
    completedTypes: ["tests_passed", "tests_failed"],
    fallbackStages: ["testing", "verifying"],
  },
  {
    key: "debugger",
    label: "Debugger",
    startedType: "debugger_started",
    completedTypes: ["debugger_completed", "fix_applied"],
    fallbackStages: ["debugging"],
  },
  {
    key: "security",
    label: "Security",
    startedType: "security_scan_started",
    completedTypes: ["security_scan_completed"],
    fallbackStages: ["security_check"],
  },
];

/**
 * Computes done/active/pending state for each agent row shown in the
 * workspace status grid. Prefers real signal from the event stream
 * (started/completed event types); falls back to inferring position from
 * the task's current status when no matching events have arrived yet.
 */
export function computeAgentStatuses(status: TaskStatus, events: AgentEvent[]): AgentRow[] {
  const currentIndex = stageIndex(status);
  const terminalDone = status === "succeeded";
  const terminalFailed = status === "failed";

  return AGENT_DEFS.map((def) => {
    const relevant = events.filter(
      (e) => e.type === def.startedType || def.completedTypes.includes(e.type)
    );
    if (relevant.length > 0) {
      const last = relevant[relevant.length - 1];
      const state: AgentRunState = def.completedTypes.includes(last.type) ? "done" : "active";
      return { key: def.key, label: def.label, state };
    }

    // Fallback purely from task status when no events are available yet.
    const fallbackIndices = def.fallbackStages.map((s) => stageIndex(s));
    const minIdx = Math.min(...fallbackIndices);
    const maxIdx = Math.max(...fallbackIndices);

    let state: AgentRunState = "pending";
    if (terminalDone || currentIndex > maxIdx) {
      state = "done";
    } else if (currentIndex >= minIdx && currentIndex <= maxIdx && !terminalFailed) {
      state = "active";
    } else if (terminalFailed && currentIndex >= minIdx) {
      // We don't know exactly where a failed run stopped without events;
      // treat stages at/after the last known status as not-yet-confirmed.
      state = currentIndex > maxIdx ? "done" : "active";
    }
    return { key: def.key, label: def.label, state };
  });
}
