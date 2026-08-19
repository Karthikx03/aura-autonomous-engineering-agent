# Contributing to AURA

Thanks for taking a look at AURA. This is a portfolio-grade, actively
developed project — issues and PRs are welcome, but please read this before
opening one so review is quick.

## Project layout / ownership

- `backend/app/**` — FastAPI app, agents, orchestrator, sandbox, git
  integration, memory, websocket, API.
- `frontend/**` — Next.js + TypeScript + Tailwind dashboard.
- `aura-bench/**` — the 20-task benchmark suite and runner.
- `demo/**`, `scripts/**` — the offline demo project and script.
- Root docs/config (`README.md`, `ARCHITECTURE.md`, `SECURITY.md`,
  `docs/*.md`, `.env.example`, `.gitignore`, `docker-compose.yml`,
  `docker/*`, `.github/workflows/ci.yml`) — project-wide documentation and
  infrastructure.

If your change spans areas, say so in the PR description so reviewers know
what to focus on.

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # or backend/.env — both are read
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Everything via Docker

```bash
docker compose up
```

## Branch naming

Use `<type>/<short-description>`, e.g.:

- `feat/coder-agent-patch-mode`
- `fix/sandbox-timeout-cleanup`
- `docs/architecture-diagrams`
- `ci/add-bench-validate-job`

## Commit message convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add DebuggerAgent confidence threshold
fix: correct RLIMIT_AS units in local-subprocess sandbox
docs: expand SECURITY.md sandbox fallback section
ci: add frontend-build job
chore: bump pydantic to 2.9.2
refactor: extract resolve_in_root() helper
test: cover path-traversal rejection in file tools
```

Common types: `feat`, `fix`, `docs`, `ci`, `chore`, `refactor`, `test`,
`perf`. Keep the summary line under ~72 characters; add a body if the "why"
isn't obvious from the diff.

## Running tests

```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm run build
npm test   # if/when a test script is configured

# AURA-Bench harness validation (proves starter fails / solution passes
# for every task)
python3 aura-bench/runner/runner.py --validate
```

All three should pass locally before opening a PR; the same commands run in
CI (`.github/workflows/ci.yml`).

## Pull request checklist

- [ ] Branch named per the convention above.
- [ ] Commits follow Conventional Commits.
- [ ] `pytest` passes in `backend/` (if backend code changed).
- [ ] `npm run build` passes in `frontend/` (if frontend code changed).
- [ ] `python3 aura-bench/runner/runner.py --validate` passes (if
      `aura-bench/` changed).
- [ ] No secrets, API keys, or `.env` files included in the diff.
- [ ] Docs updated (`README.md`, `ARCHITECTURE.md`, `docs/*.md`) if behavior
      or setup steps changed.
- [ ] No claims of results/benchmarks that weren't actually produced by
      running the relevant tool in this repo (see the project's
      no-fabrication policy in `docs/evaluation.md`).

## Code review

Small, focused PRs are much easier to review than large ones. If a change
naturally splits (e.g. "add SecurityAgent rule" + "document it in
SECURITY.md"), consider splitting it.
