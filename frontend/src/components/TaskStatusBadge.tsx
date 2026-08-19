import type { TaskStatus } from "@/lib/api";

const STATUS_STYLES: Record<TaskStatus, string> = {
  pending: "text-text-dim border-border bg-surface-raised",
  planning: "text-violet border-violet/30 bg-violet/10",
  analyzing: "text-violet border-violet/30 bg-violet/10",
  implementing: "text-accent border-accent/30 bg-accent/10",
  testing: "text-accent border-accent/30 bg-accent/10",
  debugging: "text-warning border-warning/30 bg-warning/10",
  security_check: "text-warning border-warning/30 bg-warning/10",
  verifying: "text-accent border-accent/30 bg-accent/10",
  committing: "text-accent border-accent/30 bg-accent/10",
  succeeded: "text-success border-success/30 bg-success/10",
  failed: "text-danger border-danger/30 bg-danger/10",
};

const ACTIVE_STATUSES: TaskStatus[] = [
  "planning",
  "analyzing",
  "implementing",
  "testing",
  "debugging",
  "security_check",
  "verifying",
  "committing",
];

export default function TaskStatusBadge({ status }: { status: TaskStatus }) {
  const isActive = ACTIVE_STATUSES.includes(status);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide ${STATUS_STYLES[status]}`}
    >
      {isActive && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}
      {status.replace(/_/g, " ")}
    </span>
  );
}
