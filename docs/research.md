# Research Direction

AURA is as much a research vehicle as it is a working tool: it exists to
generate real, reproducible evidence about how autonomous coding agents
behave, using AURA-Bench (`aura-bench/`) as the measurement instrument. The
questions below are **open** — nothing in this repository claims to have
answered them yet, because no full experimental run has been committed at
the time of writing. Any future answer belongs here only once it's backed
by a result file under `aura-bench/results/` (see `docs/evaluation.md`).

## Open questions this project is designed to help answer

1. **Does iterative agent execution improve coding task success rate
   compared to a single-shot attempt?** AURA's bounded plan → implement →
   test → debug → retest loop exists specifically to let this be measured:
   run the same task with `MAX_ITERATIONS=1` versus `MAX_ITERATIONS=5` and
   compare pass rates on AURA-Bench.

2. **Does a specialized multi-agent architecture (Planner / Coder /
   Debugger / Tester / Security as separate roles) outperform a single
   general-purpose agent doing everything in one pass?** This requires a
   controlled comparison against a single-agent baseline that isn't built
   yet.

3. **How much does automated test execution improve reliability of
   agent-produced code**, versus an agent that edits code and stops without
   ever running a test suite against it?

4. **How does sandboxing affect both safety and measured task success?**
   Does forcing execution through `SandboxManager` (Docker mode vs. the
   local-subprocess fallback) change outcomes, beyond the isolation
   guarantees discussed in `SECURITY.md`?

5. **Which LLM provider performs best on which subtask?** AURA's
   provider-agnostic `LLMProvider` interface (OpenAI, Anthropic, Gemini,
   Ollama, plus the deterministic `MockProvider` baseline) makes an
   apples-to-apples per-agent-role comparison possible in principle — it
   has not yet been run.

6. **How many iterations are actually optimal** before returns diminish or
   an agent starts thrashing (repeatedly proposing fixes that don't
   converge)? `IterationRecord` history is captured precisely so this kind
   of curve could be plotted from real runs.

7. **Do autonomous agents reduce regressions**, i.e. do AURA's test-and
   security-gated commits result in fewer broken changes reaching a
   repository than an ungated "just apply the diff" agent would produce?

## How AURA-Bench is meant to be used for this

Each of the 20 AURA-Bench tasks is small and independently scored, which
keeps any future experiment cheap to run and easy to reproduce: pick a
configuration (provider, `max_iterations`, sandbox mode), run the
orchestrator against every task's `starter/`, score against `tests/`, and
record the result. See `docs/evaluation.md` for the harness-validation
methodology (`--validate`) that this all depends on being trustworthy in
the first place.

## What's explicitly not claimed here

- No pass/fail numbers, latency figures, or provider rankings are stated in
  this document or anywhere else in the repository unless they were
  produced by actually running the runner and are cited from a file in
  `aura-bench/results/`.
- A 20-task benchmark is a starting point for exploring these questions,
  not a statistically powered study — a larger task set is listed as a
  roadmap item (see `README.md`) precisely because 20 tasks is not enough
  to draw strong statistical conclusions on its own.
