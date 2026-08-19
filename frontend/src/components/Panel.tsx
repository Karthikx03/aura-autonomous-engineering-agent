import type { ReactNode } from "react";

export default function Panel({
  title,
  action,
  children,
  className = "",
}: {
  title?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`flex flex-col rounded border border-border bg-surface ${className}`}>
      {title && (
        <header className="flex items-center justify-between border-b border-border px-3.5 py-2.5">
          <h2 className="text-[11px] font-semibold uppercase tracking-wide text-text-dim">
            {title}
          </h2>
          {action}
        </header>
      )}
      <div className="flex-1 p-3.5">{children}</div>
    </section>
  );
}
