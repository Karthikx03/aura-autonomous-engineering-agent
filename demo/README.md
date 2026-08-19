# AURA demo

`demo/broken_project` is a tiny, self-contained, stdlib-only Python project
(a task list manager) with one deliberate, documented bug (see
`broken_project/FIX.md`). It exists to give AURA something real to fix.

There are two ways to run the demo.

## 1. Offline scripted demo (always works, no API key needed)

```bash
bash scripts/run_demo.sh
```

This reproduces AURA's analyze -> fail -> fix -> verify -> report loop
against `demo/broken_project` end to end, with real captured `pytest`
output at every stage:

1. Lists the repository files ("repository analyzed").
2. Runs `pytest` against the broken code and shows the real failures.
3. Applies the documented fix from `broken_project/FIX.md` via a scripted,
   deterministic text edit. The script is explicit that this step is
   **not** a live LLM call - it's AURA's autonomous loop reproduced
   deterministically for the demo, standing in for the same fix a live
   LLM-backed CoderAgent+DebuggerAgent pair would derive from the test
   failure, so the demo works offline with zero setup.
4. Re-runs `pytest` and shows the real passing output.
5. Prints a final report (Task / Attempts / Root Cause / Affected Files /
   Corrective Action / Final Result / Tests / Regression Risk) populated
   entirely with real values captured from the run above.
6. Restores `demo/broken_project` back to its original broken state, so
   the script can be re-run any number of times.

## 2. Live demo through the real backend (needs a configured LLM provider)

Once the FastAPI backend is running and has an LLM provider configured
(see `backend/`), you can point AURA's real Orchestrator at the same
broken project instead of the scripted stand-in:

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Fix the failing tests in this project", "repo_path": "demo/broken_project"}'
```

This is the live path: a real CoderAgent/DebuggerAgent pair investigates
the actual test failures and proposes a fix itself. It may take more than
one iteration to converge, and its exact behavior (how it phrases the
fix, how many attempts it takes, whether it needs a hint) depends on
which LLM provider and model is configured on the backend - unlike the
offline script, this path is not scripted or guaranteed to reproduce
identical output run to run.
