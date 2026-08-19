# Getting Started

This is a step-by-step first-run guide for AURA. It assumes a Unix-like
shell, Python 3.12+, and Node.js 22+. Docker is optional but recommended
(see `SECURITY.md` for why).

## 1. Clone the repository

```bash
git clone https://github.com/<your-username>/aura-autonomous-engineering-agent.git
cd aura-autonomous-engineering-agent
```

## 2. Configure environment variables

```bash
cp .env.example .env
```

You do not need to fill in any LLM API key to run AURA. Leaving
`DEFAULT_LLM_PROVIDER=mock` (the default) uses the deterministic, offline
`MockProvider`, which is exactly what the test suite, CI, and the demo
script use. Add a real key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`,
`GOOGLE_API_KEY`, or an `OLLAMA_BASE_URL`) only once you want to drive the
agents with a real model. See `.env.example` for every supported variable.

## 3. Set up the backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API serves on `http://localhost:8000` by default. Run the backend test
suite to confirm the setup works:

```bash
pytest
```

## 4. Set up the frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

The dashboard serves on `http://localhost:3000`. If the backend isn't
reachable, the UI falls back to clearly-labeled sample data rather than
silently showing nothing — you'll still be able to see the layout and
pages before wiring the backend up.

## 5. Or run everything with Docker

```bash
docker compose up
```

This starts `frontend`, `backend`, `postgres`, and `redis`. See
`docker-compose.yml`; the observability stack (Prometheus/Grafana) is
opt-in via `docker compose --profile observability up`.

## 6. Run the offline demo

No API keys required:

```bash
bash scripts/run_demo.sh
```

This drives AURA against the small deliberately-broken sample project in
`demo/broken_project` through: analyze → test (fail) → fix → test (pass) →
report, entirely offline via `MockProvider`. Once you've configured a real
LLM key, the same `demo/broken_project` repository can be driven through the
live backend/API instead — see the comments in `scripts/run_demo.sh`.

## 7. Validate the benchmark harness

```bash
python3 aura-bench/runner/runner.py --validate
```

This actually runs, for every one of AURA-Bench's 20 tasks, the starter
code against its pytest harness (which must fail) and the reference
solution against the same harness (which must pass), and writes the result
to `aura-bench/results/`. This is how the benchmark's own correctness is
verified — see `docs/evaluation.md` for the full methodology.

## Next steps

- Read `ARCHITECTURE.md` for how the pieces fit together.
- Read `SECURITY.md` before pointing AURA at any repository you don't fully
  trust, especially regarding the Docker-vs-fallback sandbox distinction.
- Read `docs/agents.md` for what each agent actually does and its
  input/output schema.
