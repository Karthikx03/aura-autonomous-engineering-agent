import Link from "next/link";
import Panel from "@/components/Panel";

export default function AgentWorkspaceIndexPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-5">
      <h1 className="text-lg font-semibold text-text">Agent Workspace</h1>
      <Panel>
        <div className="flex flex-col items-start gap-3 py-4">
          <p className="text-[12.5px] text-text-dim">
            No task selected. Start a new task from the dashboard, or open an existing task
            from history to see its live plan, agent status, and event stream here.
          </p>
          <div className="flex gap-2">
            <Link
              href="/"
              className="rounded border border-accent/40 bg-accent/10 px-3.5 py-1.5 text-[12px] font-medium text-accent hover:bg-accent/20"
            >
              Start a new task
            </Link>
            <Link
              href="/history"
              className="rounded border border-border px-3.5 py-1.5 text-[12px] font-medium text-text-dim hover:border-border-strong hover:text-text"
            >
              Browse history
            </Link>
          </div>
        </div>
      </Panel>
    </div>
  );
}
