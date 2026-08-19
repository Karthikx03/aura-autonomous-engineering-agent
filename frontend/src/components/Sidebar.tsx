"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "◆" },
  { href: "/agent-workspace", label: "Agent Workspace", icon: "◈" },
  { href: "/code", label: "Code", icon: "◧" },
  { href: "/execution", label: "Execution", icon: "▶" },
  { href: "/tests", label: "Tests", icon: "✓" },
  { href: "/security", label: "Security", icon: "◉" },
  { href: "/history", label: "History", icon: "▤" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <nav className="flex w-52 shrink-0 flex-col border-r border-border bg-surface py-3">
      <ul className="flex flex-col gap-0.5 px-2">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          return (
            <li key={item.href}>
              <Link
                href={item.href}
                className={`flex items-center gap-2.5 rounded px-2.5 py-2 text-[12.5px] transition-colors ${
                  active
                    ? "border border-accent/30 bg-accent/10 text-accent"
                    : "border border-transparent text-text-dim hover:border-border hover:bg-surface-raised hover:text-text"
                }`}
              >
                <span className="w-3.5 text-center text-[11px] opacity-80">{item.icon}</span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
      <div className="mt-auto space-y-1 border-t border-border px-4 pt-3 text-[10.5px] leading-relaxed text-text-faint">
        <p>AURA v0.1.0</p>
        <p>Autonomous engineering agent</p>
      </div>
    </nav>
  );
}
