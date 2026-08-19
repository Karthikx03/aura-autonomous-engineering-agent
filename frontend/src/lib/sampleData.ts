/**
 * Sample/demo data used as a fallback whenever the live backend cannot be
 * reached. Every page that uses this data must render a visible
 * "Sample data — backend not connected" badge alongside it (see
 * src/components/SampleDataBadge.tsx) so the UI is always honest about
 * whether it is showing live or fallback data.
 */
import type {
  AgentEvent,
  MetricsResponse,
  ProvidersResponse,
  SecurityReport,
  TaskState,
  TestReport,
} from "./api";

export const SAMPLE_TASK_ID = "sample-task-0001";

export const sampleProviders: ProvidersResponse = {
  available: ["anthropic", "openai", "local"],
  default: "anthropic",
};

export const sampleTestReport: TestReport = {
  total: 42,
  passed: 38,
  failed: 3,
  skipped: 1,
  coverage_percent: 87.4,
  duration_seconds: 12.8,
  failures: [
    {
      name: "test_parser::handles_empty_input",
      message: "AssertionError: expected ValueError, got IndexError",
    },
    {
      name: "test_api::rejects_invalid_repo_path",
      message: "TimeoutError: request exceeded 5s",
    },
    {
      name: "test_utils::normalizes_paths_on_windows",
      message: "AssertionError: 'a\\\\b' != 'a/b'",
    },
  ],
  raw_output:
    "===== 42 tests collected =====\n... 38 passed, 3 failed, 1 skipped in 12.80s\n",
};

export const sampleSecurityReport: SecurityReport = {
  issues: [
    {
      rule_id: "B608",
      severity: "high",
      file: "app/db/queries.py",
      line: 114,
      message: "Possible SQL injection via string-formatted query.",
    },
    {
      rule_id: "B105",
      severity: "medium",
      file: "app/auth/tokens.py",
      line: 22,
      message: "Hardcoded password/token string detected.",
    },
    {
      rule_id: "B301",
      severity: "low",
      file: "app/utils/cache.py",
      line: 58,
      message: "Use of pickle module may allow deserialization of untrusted data.",
    },
    {
      rule_id: "S001",
      severity: "info",
      file: "app/main.py",
      line: 9,
      message: "Debug mode flag found; ensure it is disabled in production.",
    },
  ],
};

export const sampleMetrics: MetricsResponse = {
  tool_calls_total: { read_file: 214, write_file: 63, run_tests: 41, run_command: 88 },
  tool_call_errors_total: { read_file: 2, run_tests: 5, run_command: 3 },
  agent_events_total: {
    task_started: 12,
    planner_completed: 12,
    coder_completed: 46,
    tests_passed: 9,
    tests_failed: 5,
    task_completed: 10,
    task_failed: 2,
  },
  llm_calls_total: { anthropic: 312, openai: 94, local: 18 },
  tasks_completed: 10,
  avg_task_duration_seconds: 184.5,
  avg_llm_latency_seconds: 2.3,
};

export const sampleTasks: TaskState[] = [
  {
    task_id: SAMPLE_TASK_ID,
    goal: "Fix the deliberately broken demo project",
    repo_path: "demo/broken_project",
    status: "succeeded",
    max_iterations: 5,
    iteration: 3,
    plan: {
      goal: "Fix the deliberately broken demo project",
      requirements: [
        "Restore passing test suite",
        "Do not change public API signatures",
        "Keep changes minimal and reviewable",
      ],
      tasks: [
        "Locate failing tests and reproduce locally",
        "Identify root cause in parser module",
        "Apply fix and re-run full test suite",
        "Run security scan on changed files",
      ],
      files: ["app/parser.py", "app/utils/validate.py", "tests/test_parser.py"],
      tests: ["tests/test_parser.py", "tests/test_validate.py"],
      risks: [
        "Fix may mask a deeper input-validation issue",
        "Third-party dependency version mismatch",
      ],
    },
    repo_map: {
      root: "demo/broken_project",
      languages: ["Python"],
      frameworks: ["FastAPI", "pytest"],
      dependencies: ["fastapi", "pydantic", "pytest", "uvicorn"],
      test_files: ["tests/test_parser.py", "tests/test_validate.py", "tests/test_api.py"],
      has_git: true,
      file_count: 34,
      summary: "Small FastAPI service with a broken input parser and one failing endpoint.",
    },
    history: [
      {
        iteration: 1,
        summary: "Reproduced failure in parser.parse_line for empty input.",
        test_report: { ...sampleTestReport, passed: 35, failed: 6 },
        debug_report: null,
        changes: ["app/parser.py"],
        timestamp: new Date(Date.now() - 1000 * 60 * 9).toISOString(),
      },
      {
        iteration: 2,
        summary: "Added guard clause + regression test; two failures remain.",
        test_report: { ...sampleTestReport, passed: 40, failed: 1 },
        debug_report: "Timeout in test_api::rejects_invalid_repo_path traced to retry loop.",
        changes: ["app/parser.py", "app/api/routes.py"],
        timestamp: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
      },
      {
        iteration: 3,
        summary: "All tests passing; security scan clean aside from advisory findings.",
        test_report: sampleTestReport,
        debug_report: null,
        changes: ["app/api/routes.py", "tests/test_parser.py"],
        timestamp: new Date(Date.now() - 1000 * 60 * 1).toISOString(),
      },
    ],
    security_report: sampleSecurityReport,
    final_test_report: sampleTestReport,
    commit_sha: "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    started_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    finished_at: new Date(Date.now() - 1000 * 60 * 1).toISOString(),
    error: null,
  },
  {
    task_id: "sample-task-0002",
    goal: "Add rate limiting middleware to the public API",
    repo_path: "demo/broken_project",
    status: "testing",
    max_iterations: 5,
    iteration: 2,
    plan: {
      goal: "Add rate limiting middleware to the public API",
      requirements: ["429 responses under burst load", "Configurable limits per route"],
      tasks: ["Add middleware", "Write load test", "Document config"],
      files: ["app/middleware/rate_limit.py"],
      tests: ["tests/test_rate_limit.py"],
      risks: ["Could affect latency on hot path"],
    },
    repo_map: null,
    history: [
      {
        iteration: 1,
        summary: "Implemented token-bucket limiter.",
        test_report: null,
        debug_report: null,
        changes: ["app/middleware/rate_limit.py"],
        timestamp: new Date(Date.now() - 1000 * 60 * 3).toISOString(),
      },
    ],
    security_report: null,
    final_test_report: null,
    commit_sha: null,
    started_at: new Date(Date.now() - 1000 * 60 * 4).toISOString(),
    finished_at: null,
    error: null,
  },
  {
    task_id: "sample-task-0003",
    goal: "Migrate config loader to pydantic-settings",
    repo_path: "demo/broken_project",
    status: "failed",
    max_iterations: 4,
    iteration: 4,
    plan: null,
    repo_map: null,
    history: [],
    security_report: null,
    final_test_report: { ...sampleTestReport, passed: 20, failed: 10, total: 30 },
    commit_sha: null,
    started_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    finished_at: new Date(Date.now() - 1000 * 60 * 50).toISOString(),
    error: "Exceeded max_iterations without a passing test suite.",
  },
];

export const sampleEvents: AgentEvent[] = [
  {
    type: "task_started",
    agent: "orchestrator",
    message: "Task started: Fix the deliberately broken demo project",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 720,
  },
  {
    type: "planner_started",
    agent: "planner",
    message: "Analyzing goal and drafting execution plan",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 710,
  },
  {
    type: "planner_completed",
    agent: "planner",
    message: "Plan created with 4 tasks across 3 files",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 700,
  },
  {
    type: "repo_analysis_started",
    agent: "analyzer",
    message: "Scanning repository structure",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 695,
  },
  {
    type: "repo_analysis_completed",
    agent: "analyzer",
    message: "Repo map built: Python/FastAPI, 34 files",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 680,
  },
  {
    type: "coder_started",
    agent: "coder",
    message: "Implementing fix in app/parser.py",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 660,
  },
  {
    type: "file_modified",
    agent: "coder",
    message: "Modified app/parser.py",
    task_id: SAMPLE_TASK_ID,
    data: { file: "app/parser.py" },
    timestamp: Date.now() / 1000 - 640,
  },
  {
    type: "coder_completed",
    agent: "coder",
    message: "Changes applied for iteration 1",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 620,
  },
  {
    type: "command_executed",
    agent: "executor",
    message: "Ran: pytest -q",
    task_id: SAMPLE_TASK_ID,
    data: { command: "pytest -q", exit_code: 1, duration_seconds: 3.2 },
    timestamp: Date.now() / 1000 - 600,
  },
  {
    type: "tests_failed",
    agent: "tester",
    message: "6 tests failed",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 590,
  },
  {
    type: "debugger_started",
    agent: "debugger",
    message: "Investigating failures",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 560,
  },
  {
    type: "fix_applied",
    agent: "debugger",
    message: "Applied guard clause fix",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 500,
  },
  {
    type: "tests_passed",
    agent: "tester",
    message: "42 tests passed (1 skipped)",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 200,
  },
  {
    type: "security_scan_completed",
    agent: "security",
    message: "Security scan complete: 4 advisory findings",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 120,
  },
  {
    type: "git_diff_ready",
    agent: "committer",
    message: "Diff ready for review",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 90,
  },
  {
    type: "git_commit_created",
    agent: "committer",
    message: "Committed a1b2c3d",
    task_id: SAMPLE_TASK_ID,
    data: { sha: "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678" },
    timestamp: Date.now() / 1000 - 70,
  },
  {
    type: "task_completed",
    agent: "orchestrator",
    message: "Task completed successfully",
    task_id: SAMPLE_TASK_ID,
    data: {},
    timestamp: Date.now() / 1000 - 60,
  },
];
