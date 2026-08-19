"use client";

import { useEffect, useState } from "react";
import { API_BASE, getProviders } from "@/lib/api";

export default function TopBar() {
  const [connected, setConnected] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    getProviders()
      .then(() => {
        if (!cancelled) setConnected(true);
      })
      .catch(() => {
        if (!cancelled) setConnected(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4">
      <div className="flex items-center gap-2">
        <span className="text-[15px] font-bold tracking-[0.15em] text-text">AURA</span>
        <span className="hidden text-[11px] text-text-faint sm:inline">
          autonomous software-engineering agent
        </span>
      </div>
      <div className="flex items-center gap-4">
        <span className="hidden text-[11px] text-text-faint md:inline">{API_BASE}</span>
        <StatusPill connected={connected} />
      </div>
    </header>
  );
}

function StatusPill({ connected }: { connected: boolean | null }) {
  if (connected === null) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-text-dim">
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-text-faint" />
        Checking backend…
      </span>
    );
  }

  if (connected) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-success/30 bg-success/10 px-2.5 py-1 text-[11px] text-success">
        <span className="h-1.5 w-1.5 rounded-full bg-success shadow-[0_0_6px_var(--color-success)]" />
        Autonomous Agent Ready
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-warning/30 bg-warning/10 px-2.5 py-1 text-[11px] text-warning">
      <span className="h-1.5 w-1.5 rounded-full bg-warning" />
      Backend Unreachable
    </span>
  );
}
