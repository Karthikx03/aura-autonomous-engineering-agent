# FIX.md - reference fix for demo/broken_project

## Bug

`TaskList.summary()` in `tasklist.py` computes the pending count as:

```python
pending = total - done - 1
```

That trailing `- 1` is an off-by-one bug: it undercounts pending tasks by
one whenever there is at least one pending task, and produces `-1` when
there are zero tasks at all (`0 - 0 - 1 == -1`).

## Fix

Remove the stray `- 1`:

```python
pending = total - done
```

That's the entire fix - one line, in `tasklist.py`, inside `TaskList.summary()`.

## How this is applied

`scripts/run_demo.sh` applies this exact fix with a scripted, deterministic
text replacement (no LLM call) so the demo is reproducible offline:

```
pending = total - done - 1   ->   pending = total - done
```

## Verification

Before the fix: `python3 -m pytest tests/` in this directory reports
3 failed, 1 passed (see `test_summary_counts_are_consistent`,
`test_pending_matches_summary_pending_count`, and
`test_summary_with_no_tasks`, all of which depend on a correct pending
count).

After the fix: all 4 tests pass.
