"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { type TaskState, listTasks } from "@/lib/api";
import { demoFiles } from "@/lib/demoFiles";
import { sampleTasks } from "@/lib/sampleData";
import Panel from "@/components/Panel";
import SampleDataBadge from "@/components/SampleDataBadge";

const MonacoEditor = dynamic(() => import("@monaco-editor/react"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center text-[12px] text-text-faint">
      Loading editor…
    </div>
  ),
});

export default function CodePage() {
  const [selectedPath, setSelectedPath] = useState(demoFiles[0].path);
  const [tasks, setTasks] = useState<TaskState[]>([]);
  const [usingSampleData, setUsingSampleData] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listTasks()
      .then((t) => {
        if (!cancelled) {
          setTasks(t);
          setUsingSampleData(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setTasks(sampleTasks);
          setUsingSampleData(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedFile = demoFiles.find((f) => f.path === selectedPath) ?? demoFiles[0];

  const referencedFiles = Array.from(
    new Set(
      tasks.flatMap((t) => [
        ...(t.plan?.files ?? []),
        ...(t.repo_map?.test_files ?? []),
      ])
    )
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-4 p-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-text">Code</h1>
          <p className="mt-0.5 text-[12px] text-text-dim">
            Read-only preview. AURA does not yet expose an endpoint to fetch live raw file
            content, so this browses bundled demo files — nothing here is editable/saved back.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <div className="flex flex-col gap-4 lg:col-span-1">
          <Panel title="Demo Files">
            <ul className="flex flex-col gap-0.5">
              {demoFiles.map((f) => (
                <li key={f.path}>
                  <button
                    onClick={() => setSelectedPath(f.path)}
                    className={`w-full truncate rounded px-2 py-1.5 text-left font-mono text-[11.5px] ${
                      selectedPath === f.path
                        ? "bg-accent/10 text-accent"
                        : "text-text-dim hover:bg-surface-raised hover:text-text"
                    }`}
                    title={f.path}
                  >
                    {f.path.split("/").pop()}
                  </button>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel
            title="Referenced by Tasks"
            action={usingSampleData ? <SampleDataBadge /> : undefined}
          >
            {referencedFiles.length === 0 ? (
              <p className="text-[11.5px] text-text-faint">
                No task file references available yet.
              </p>
            ) : (
              <ul className="flex flex-col gap-1 text-[11px] text-text-faint">
                {referencedFiles.slice(0, 20).map((f) => (
                  <li key={f} className="truncate font-mono" title={f}>
                    {f}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 border-t border-border pt-2 text-[10.5px] text-text-faint">
              Paths only — content for these is not fetchable via the current API.
            </p>
          </Panel>
        </div>

        <Panel title={selectedFile.path} className="lg:col-span-3">
          <div className="h-[560px] overflow-hidden rounded border border-border">
            <MonacoEditor
              height="100%"
              language={selectedFile.language}
              value={selectedFile.content}
              theme="vs-dark"
              options={{
                readOnly: true,
                fontFamily: "var(--font-mono)",
                fontSize: 12.5,
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                wordWrap: "on",
              }}
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}
