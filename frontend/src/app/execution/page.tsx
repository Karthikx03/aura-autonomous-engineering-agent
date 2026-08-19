import Link from "next/link";
import Panel from "@/components/Panel";

export default function ExecutionIndexPage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-4 p-5">
      <h1 className="text-lg font-semibold text-text">Execution</h1>
      <Panel>
        <div className="flex flex-col items-start gap-3 py-4">
          <p className="text-[12.5px] text-text-dim">
            No task selected. Pick a task from history to see its executed commands and test
            runs.
          </p>
          <Link
            href="/history"
            className="rounded border border-accent/40 bg-accent/10 px-3.5 py-1.5 text-[12px] font-medium text-accent hover:bg-accent/20"
          >
            Browse history
          </Link>
        </div>
      </Panel>
    </div>
  );
}
