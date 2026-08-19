#!/usr/bin/env bash
# AURA offline scripted demo.
#
# Runs a REAL, reproducible end-to-end sequence against demo/broken_project:
# analyze -> fail -> fix -> pass -> report -> restore.
#
# No API key or live LLM is used or required. Every command output shown
# below is captured from an actual run, not fabricated. Where the script
# applies the fix itself (step 3), it says so explicitly instead of
# pretending an LLM produced it.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT_DIR="${REPO_ROOT}/demo/broken_project"
TASKLIST_FILE="${PROJECT_DIR}/tasklist.py"
BACKUP_FILE="$(mktemp /tmp/aura-demo-tasklist-backup.XXXXXX.py)"

PY="${PYTHON:-python3}"

hr() { printf '%s\n' "------------------------------------------------------------------"; }

cleanup() {
    # Always restore the original broken file, whatever happened, so the
    # demo is repeatable.
    if [[ -f "${BACKUP_FILE}" ]]; then
        cp "${BACKUP_FILE}" "${TASKLIST_FILE}"
        rm -f "${BACKUP_FILE}"
    fi
    rm -rf "${PROJECT_DIR}/__pycache__" "${PROJECT_DIR}/tests/__pycache__" "${PROJECT_DIR}/.pytest_cache"
}
trap cleanup EXIT

if [[ ! -f "${TASKLIST_FILE}" ]]; then
    echo "ERROR: ${TASKLIST_FILE} not found. Run this from the repo, or check demo/broken_project exists." >&2
    exit 1
fi

# Keep an untouched copy so we can restore it at the end regardless of outcome.
cp "${TASKLIST_FILE}" "${BACKUP_FILE}"

echo "==================================================================="
echo " AURA autonomous fix-and-verify loop -- offline scripted demo"
echo "==================================================================="
echo
echo "This script demonstrates AURA's core loop (analyze -> reproduce"
echo "failure -> fix -> verify -> report) against a small real Python"
echo "project with a genuine, deliberately-introduced bug."
echo

# ---------------------------------------------------------------------------
# Step 1: "repository analyzed"
# ---------------------------------------------------------------------------
hr
echo "STEP 1/5: Analyze repository"
hr
echo "\$ find demo/broken_project -type f"
find "${PROJECT_DIR}" -type f | sed "s|${REPO_ROOT}/||" | sort
echo
echo "Repository analyzed: 1 module (tasklist.py), 1 CLI entrypoint (cli.py),"
echo "1 test file (tests/test_tasklist.py)."
echo

# ---------------------------------------------------------------------------
# Step 2: run pytest, show the real failure
# ---------------------------------------------------------------------------
hr
echo "STEP 2/5: Run tests against the current (broken) code"
hr
echo "\$ python3 -m pytest tests/ -q"
set +e
BEFORE_OUTPUT="$(cd "${PROJECT_DIR}" && "${PY}" -m pytest tests/ -q 2>&1)"
BEFORE_STATUS=$?
set -e
echo "${BEFORE_OUTPUT}"
echo
if [[ ${BEFORE_STATUS} -eq 0 ]]; then
    echo "ERROR: expected the starter project's tests to fail, but they passed." >&2
    exit 1
fi
BEFORE_SUMMARY_LINE="$(echo "${BEFORE_OUTPUT}" | grep -E '[0-9]+ (passed|failed|error)' | tail -1)"
echo "Result: FAIL as expected -> ${BEFORE_SUMMARY_LINE}"
echo

# ---------------------------------------------------------------------------
# Step 3: apply the documented fix (scripted, deterministic - no LLM)
# ---------------------------------------------------------------------------
hr
echo "STEP 3/5: Apply fix"
hr
echo "AURA's autonomous loop reproduced deterministically for the demo -- the"
echo "same fix a live LLM-backed CoderAgent+DebuggerAgent pair would derive"
echo "from the test failure above, applied here with a scripted text edit"
echo "instead of a live model call, so this demo runs reproducibly offline"
echo "with no API key. See demo/broken_project/FIX.md for the human-readable"
echo "root-cause writeup this edit is taken from."
echo
echo "\$ python3 -c \"... replace 'pending = total - done - 1' with 'pending = total - done' in tasklist.py ...\""

BEFORE_LINE="$(grep -n 'pending = total - done - 1' "${TASKLIST_FILE}" || true)"
if [[ -z "${BEFORE_LINE}" ]]; then
    echo "ERROR: expected buggy line 'pending = total - done - 1' not found in tasklist.py" >&2
    exit 1
fi
echo "Found buggy line: ${BEFORE_LINE}"

"${PY}" - "${TASKLIST_FILE}" <<'PYEOF'
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as fh:
    content = fh.read()

buggy = "pending = total - done - 1"
fixed = "pending = total - done"
if buggy not in content:
    raise SystemExit("buggy line not found - refusing to write an unexpected file")

content = content.replace(buggy, fixed)
with open(path, "w", encoding="utf-8") as fh:
    fh.write(content)
PYEOF

AFTER_LINE="$(grep -n 'pending = total - done$' "${TASKLIST_FILE}" || true)"
echo "Applied fix, new line: ${AFTER_LINE}"
echo

# ---------------------------------------------------------------------------
# Step 4: rerun pytest, show the real pass
# ---------------------------------------------------------------------------
hr
echo "STEP 4/5: Re-run tests against the fixed code"
hr
echo "\$ python3 -m pytest tests/ -q"
set +e
AFTER_OUTPUT="$(cd "${PROJECT_DIR}" && "${PY}" -m pytest tests/ -q 2>&1)"
AFTER_STATUS=$?
set -e
echo "${AFTER_OUTPUT}"
echo
if [[ ${AFTER_STATUS} -ne 0 ]]; then
    echo "ERROR: expected tests to pass after the fix, but they failed." >&2
    exit 1
fi
AFTER_SUMMARY_LINE="$(echo "${AFTER_OUTPUT}" | grep -E '[0-9]+ (passed|failed|error)' | tail -1)"
echo "Result: PASS -> ${AFTER_SUMMARY_LINE}"
echo

# ---------------------------------------------------------------------------
# Step 5: final report, built from real values captured above
# ---------------------------------------------------------------------------
hr
echo "STEP 5/5: Final report"
hr
cat <<REPORT
FAILURE ANALYSIS / RESOLUTION REPORT

Task:              Fix incorrect pending-task count in demo/broken_project
Attempts:           1
Root Cause:         Off-by-one error in TaskList.summary() (tasklist.py) --
                     'pending = total - done - 1' subtracted an extra 1,
                     undercounting pending tasks by one (and producing -1
                     when there were zero tasks at all).
Affected Files:     demo/broken_project/tasklist.py
Corrective Action:  Removed the stray '- 1': 'pending = total - done - 1'
                     -> 'pending = total - done'.
Final Result:       SUCCESS
Tests:              before: ${BEFORE_SUMMARY_LINE}
                     after:  ${AFTER_SUMMARY_LINE}
Regression Risk:    Low. Single-line arithmetic fix confined to one
                     already-covered function; all 4 tests in
                     tests/test_tasklist.py now pass and no other code
                     path reads the old (buggy) expression.
REPORT
echo

# ---------------------------------------------------------------------------
# Step 6 (implicit): restore the original broken file so the demo repeats.
# Handled by the cleanup() trap registered above, which always fires,
# including on error - so the repo is left exactly as it was found.
# ---------------------------------------------------------------------------
hr
echo "Restoring demo/broken_project to its original (broken) state so the"
echo "demo can be re-run..."
hr
