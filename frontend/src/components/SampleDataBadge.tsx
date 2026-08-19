export default function SampleDataBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border border-warning/30 bg-warning/10 px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-wide text-warning ${className}`}
      title="The live backend could not be reached; this view is showing bundled sample data."
    >
      <span className="h-1.5 w-1.5 rounded-full bg-warning" />
      Sample data — backend not connected
    </span>
  );
}
