"""CoderAgent: asks the LLM for a structured edit list and applies it via tools.

The agent never overwrites the repository wholesale. It asks the LLM for a
small JSON list of edits (``{"path", "action", "content_or_patch"}``) and
then performs exactly those edits through the injected ``ToolRegistry`` --
``write_file`` for create/overwrite, ``edit_file`` for a find/replace patch,
and nothing else. The ``CodeChange`` objects returned reflect the tool call
results, not the LLM's claims.
"""
from __future__ import annotations

import json

from app.agents.base import BaseAgent
from app.llm.base import LLMMessage
from app.orchestrator.state import CodeChange, DebugReport, PlanResult

_SYSTEM_PROMPT = (
    "You are the coding agent of AURA. Given an implementation plan (and, if "
    "present, a proposed fix from a previous failed attempt), produce the "
    "concrete file edits needed. Respond with a single JSON object: "
    '{"edits": [{"path": "relative/path", "action": "create"|"modify"|"delete", '
    '"content_or_patch": "..."}]}. For action "create" or "modify" without a '
    'find/replace patch, content_or_patch is the full file content to write. '
    'For a targeted patch, content_or_patch may instead be an object '
    '{"find": "...", "replace": "..."}. Respond with JSON only.'
)


class CoderAgent(BaseAgent):
    name = "coder"

    async def implement(
        self,
        plan: PlanResult,
        repo_path: str,
        debug_report: DebugReport | None = None,
    ) -> list[CodeChange]:
        self.emit("Implementation started", goal=plan.goal, files=plan.files)

        edits = await self._request_edits(plan, repo_path, debug_report)
        changes = await self._apply_edits(edits, repo_path)

        self.emit("Implementation completed", changes=len(changes))
        return changes

    async def _request_edits(
        self,
        plan: PlanResult,
        repo_path: str,
        debug_report: DebugReport | None,
    ) -> list[dict]:
        prompt_lines = [
            f"Implementation plan for goal: {plan.goal}",
            f"Requirements: {plan.requirements}",
            f"Tasks: {plan.tasks}",
            f"Target files: {plan.files}",
            f"Repository path: {repo_path}",
        ]
        if debug_report is not None:
            prompt_lines.append(
                "A previous attempt failed. Apply this proposed fix as a "
                f"follow-up edit: root_cause={debug_report.root_cause!r}, "
                f"proposed_fix={debug_report.proposed_fix!r}, "
                f"affected_files={debug_report.affected_files}"
            )
        prompt_lines.append('Return {"edits": [...]} as described.')
        prompt = "\n".join(prompt_lines)

        messages = [
            LLMMessage(role="system", content=_SYSTEM_PROMPT),
            LLMMessage(role="user", content=prompt),
        ]

        response = await self.llm.complete(messages, json_mode=True)

        try:
            parsed = json.loads(response.content)
            edits = parsed.get("edits", []) if isinstance(parsed, dict) else []
            if not isinstance(edits, list):
                edits = []
        except Exception as exc:
            self.emit("Coder edit-list JSON parse failed, no edits applied", error=str(exc))
            edits = []
        return edits

    async def _apply_edits(self, edits: list[dict], repo_path: str) -> list[CodeChange]:
        changes: list[CodeChange] = []
        if self.tools is None:
            self.emit("No tool registry available; skipping edit application")
            return changes

        for edit in edits:
            if not isinstance(edit, dict):
                continue
            path = edit.get("path")
            action = (edit.get("action") or "modify").lower()
            payload = edit.get("content_or_patch")
            if not path:
                continue

            try:
                if action == "delete":
                    result = await self.tools.call(
                        "write_file", path=path, content="", agent=self.name
                    )
                    if result.ok:
                        changes.append(CodeChange(path=path, action="deleted", diff_preview=""))
                    continue

                if isinstance(payload, dict) and "find" in payload and "replace" in payload:
                    result = await self.tools.call(
                        "edit_file",
                        path=path,
                        find=payload["find"],
                        replace=payload["replace"],
                        agent=self.name,
                    )
                    if result.ok:
                        preview = f"replaced {result.output.get('replacements', '?')} occurrence(s)" \
                            if isinstance(result.output, dict) else ""
                        changes.append(
                            CodeChange(path=path, action="modified", diff_preview=preview)
                        )
                    else:
                        self.emit("Edit failed", path=path, error=result.error)
                    continue

                content = payload if isinstance(payload, str) else json.dumps(payload)
                result = await self.tools.call(
                    "write_file", path=path, content=content, agent=self.name
                )
                if result.ok:
                    resolved_action = "created" if action == "create" else "modified"
                    preview = content[:200]
                    changes.append(
                        CodeChange(path=path, action=resolved_action, diff_preview=preview)
                    )
                else:
                    self.emit("Write failed", path=path, error=result.error)
            except KeyError as exc:
                self.emit("Tool not available", error=str(exc))

        return changes
