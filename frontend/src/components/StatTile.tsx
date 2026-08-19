export default function StatTile({
  label,
  value,
  sublabel,
  accent = false,
}: {
  label: string;
  value: string | number;
  sublabel?: string;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded border border-border bg-surface p-4">
      <span className="text-[10.5px] uppercase tracking-wide text-text-faint">{label}</span>
      <span className={`text-2xl font-semibold ${accent ? "text-accent" : "text-text"}`}>
        {value}
      </span>
      {sublabel && <span className="text-[11px] text-text-dim">{sublabel}</span>}
    </div>
  );
}
