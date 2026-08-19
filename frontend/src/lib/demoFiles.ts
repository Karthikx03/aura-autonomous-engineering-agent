export interface DemoFile {
  path: string;
  language: string;
  content: string;
}

/**
 * Static bundled files used for the /code viewer. The backend contract does
 * not currently expose an endpoint for reading raw file contents from a
 * task's repository (only file *paths* via plan.files / repo_map.test_files),
 * so this viewer previews these representative demo files rather than
 * pretending to stream live repo content.
 */
export const demoFiles: DemoFile[] = [
  {
    path: "demo/broken_project/app/parser.py",
    language: "python",
    content: `def parse_line(line: str) -> dict:
    """Parse a single log line into a structured record.

    Historically raised IndexError on empty input instead of a
    descriptive ValueError -- this is the bug AURA's demo task fixes.
    """
    if not line.strip():
        raise ValueError("cannot parse an empty line")

    parts = line.strip().split("|")
    if len(parts) < 3:
        raise ValueError(f"expected at least 3 fields, got {len(parts)}")

    return {
        "timestamp": parts[0],
        "level": parts[1],
        "message": "|".join(parts[2:]),
    }
`,
  },
  {
    path: "demo/broken_project/app/api/routes.py",
    language: "python",
    content: `from fastapi import APIRouter, HTTPException

from app.parser import parse_line

router = APIRouter()


@router.post("/parse")
async def parse(payload: dict):
    try:
        return parse_line(payload.get("line", ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
`,
  },
  {
    path: "demo/broken_project/tests/test_parser.py",
    language: "python",
    content: `import pytest

from app.parser import parse_line


def test_parses_well_formed_line():
    record = parse_line("2026-08-19T00:00:00|INFO|service started")
    assert record["level"] == "INFO"


def test_handles_empty_input():
    with pytest.raises(ValueError):
        parse_line("")


def test_rejects_short_line():
    with pytest.raises(ValueError):
        parse_line("only|two")
`,
  },
  {
    path: "demo/broken_project/README.md",
    language: "markdown",
    content: `# broken_project

A deliberately broken demo FastAPI service used to exercise AURA end to end.

Run \`pytest\` to see the seeded failures AURA is expected to diagnose and fix.
`,
  },
];
