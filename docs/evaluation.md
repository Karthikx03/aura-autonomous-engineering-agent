# Evaluation: AURA-Bench

AURA-Bench (`aura-bench/`) is a small, hand-built benchmark of real software
engineering micro-tasks, used to measure whether AURA (or any agent, human
or automated) can actually fix a broken piece of code — not to claim a
polished leaderboard number. This document explains the methodology and,
importantly, where any numbers you see actually come from.

## What a task is

Each of the 20 tasks under `aura-bench/tasks/task-XX-<name>/` is a small,
independently runnable unit with three parts:

- `starter/` — a small real project with one deliberate, specific bug or
  missing piece (an off-by-one error, a missing endpoint, an unhandled
  error path, a race condition, a mutable-default-argument bug, etc.).
- `tests/` — a pytest harness for that task that encodes the correct
  behavior. It is written against the *interface*, not the buggy
  implementation, so it genuinely fails against `starter/` and genuinely
  passes against `solution/`.
- `solution/` — a reference fix, used only to validate the harness itself
  (see below), not shown to the agent under test.

Task topics span typical day-to-day engineering work: API routes, auth
bugs, DB migrations, import shims, off-by-one errors, missing endpoints,
race conditions, error handling, regex validation, pagination, sort
comparators, SQL WHERE clauses, stale caches, JSON/datetime handling, CORS
headers, env var handling, retry/backoff logic, Docker config, and mutable
default arguments.

## Why the harness has to be validated, not trusted

A benchmark task is only meaningful if its test harness actually
discriminates broken code from correct code. It's easy to accidentally
write a test that passes against both the buggy starter and the fixed
solution (a tautology), or one that fails against both (broken tooling). To
rule that out mechanically, `aura-bench/runner/runner.py` supports a
`--validate` mode:

```bash
python3 aura-bench/runner/runner.py --validate
```

For **every** task, this actually:

1. Copies `starter/` into a scratch directory and runs `tests/` against
   it — this run **must fail** (if it passes, the harness doesn't actually
   test the bug).
2. Copies `solution/` into a scratch directory and runs `tests/` against
   it — this run **must pass** (if it fails, either the reference solution
   or the harness is wrong).
3. Writes the outcome for every task to a timestamped JSON file under
   `aura-bench/results/`.

If either check fails for any task, `--validate` reports it — this is how
we catch a broken task definition rather than silently trusting it.

## Running the agent against the benchmark

Beyond `--validate` (which only proves the harness itself is sound), the
runner can also drive AURA's Orchestrator against each task's `starter/`
and score the outcome against `tests/`. This mode requires a configured
LLM provider (or runs against `MockProvider`'s deterministic, limited
behavior if none is configured) — see `.env.example`.

## Honesty policy for numbers

**Any pass-rate, score, or benchmark number that appears anywhere in this
repository (README, docs, PR descriptions, commit messages) must come from
actually running the runner/validator in this repository and citing the
resulting file under `aura-bench/results/`.** Nothing is estimated, rounded
up, or carried over from a different run without saying so. If no
`--validate` or full-benchmark run has been committed yet, the honest
statement is "not yet run" — not a plausible-sounding number.

## Reproducing a result

```bash
cd /path/to/aura-autonomous-engineering-agent
python3 aura-bench/runner/runner.py --validate
cat aura-bench/results/<the JSON file it wrote>
```

`aura-bench/results/*.json` is intentionally **not** gitignored — those
files are the artifact that makes any benchmark claim in this repository
checkable.
