const SEVERITY_STYLES: Record<string, string> = {
  critical: "text-danger border-danger/40 bg-danger/10",
  high: "text-danger border-danger/30 bg-danger/10",
  medium: "text-warning border-warning/30 bg-warning/10",
  low: "text-accent border-accent/30 bg-accent/10",
  info: "text-text-dim border-border bg-surface-raised",
};

export default function SeverityBadge({ severity }: { severity: string }) {
  const style = SEVERITY_STYLES[severity.toLowerCase()] ?? SEVERITY_STYLES.info;
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide ${style}`}
    >
      {severity}
    </span>
  );
}
