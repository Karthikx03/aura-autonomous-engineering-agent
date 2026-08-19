"""Tests for app.memory.models / app.memory.db.

Uses a tmp-file sqlite database rather than ``:memory:`` -- async sqlite
with an in-memory DB needs a single shared connection to avoid each new
connection seeing an empty (freshly-created) database, which is easy to get
wrong via the pool; a tmp file sidesteps that entirely and behaves like a
real deployment.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from app.memory.db import get_sessionmaker, init_db
from app.memory.models import AgentDecisionModel, FileChangeModel, IterationRecordModel, Project, TaskRun


def _db_url(tmp_path: Path) -> str:
    db_file = tmp_path / "test_aura.db"
    return f"sqlite+aiosqlite:///{db_file}"


@pytest.mark.asyncio
async def test_init_db_creates_tables(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    await init_db(url)
    sessionmaker = get_sessionmaker(url)
    async with sessionmaker() as session:
        result = await session.execute(select(Project))
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_project_and_task_run_round_trip(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    await init_db(url)
    sessionmaker = get_sessionmaker(url)

    async with sessionmaker() as session:
        project = Project(name="aura-demo", repo_path="/tmp/aura-demo")
        session.add(project)
        await session.flush()

        task_run = TaskRun(
            project_id=project.id,
            goal="Add a health check endpoint",
            status="succeeded",
            iterations=2,
            tests_passed=5,
            tests_failed=0,
            success=True,
        )
        session.add(task_run)
        await session.commit()
        task_run_id = task_run.id
        project_id = project.id

    async with sessionmaker() as session:
        fetched_project = await session.get(Project, project_id)
        assert fetched_project is not None
        assert fetched_project.name == "aura-demo"
        assert fetched_project.repo_path == "/tmp/aura-demo"
        assert fetched_project.created_at is not None

        fetched_task_run = await session.get(TaskRun, task_run_id)
        assert fetched_task_run is not None
        assert fetched_task_run.goal == "Add a health check endpoint"
        assert fetched_task_run.status == "succeeded"
        assert fetched_task_run.iterations == 2
        assert fetched_task_run.tests_passed == 5
        assert fetched_task_run.success is True
        assert fetched_task_run.project_id == project_id


@pytest.mark.asyncio
async def test_iteration_file_change_and_agent_decision_round_trip(tmp_path: Path) -> None:
    url = _db_url(tmp_path)
    await init_db(url)
    sessionmaker = get_sessionmaker(url)

    async with sessionmaker() as session:
        project = Project(name="p", repo_path="/tmp/p")
        session.add(project)
        await session.flush()

        task_run = TaskRun(project_id=project.id, goal="g", status="running", iterations=0)
        session.add(task_run)
        await session.flush()

        session.add(
            IterationRecordModel(
                task_run_id=task_run.id, iteration=1, summary="did stuff", tests_passed=1, tests_failed=0
            )
        )
        session.add(FileChangeModel(task_run_id=task_run.id, path="app/foo.py", action="modified"))
        session.add(AgentDecisionModel(task_run_id=task_run.id, agent="coder", message="edited foo.py"))
        await session.commit()
        task_run_id = task_run.id

    async with sessionmaker() as session:
        iterations = (
            await session.execute(select(IterationRecordModel).where(IterationRecordModel.task_run_id == task_run_id))
        ).scalars().all()
        changes = (
            await session.execute(select(FileChangeModel).where(FileChangeModel.task_run_id == task_run_id))
        ).scalars().all()
        decisions = (
            await session.execute(select(AgentDecisionModel).where(AgentDecisionModel.task_run_id == task_run_id))
        ).scalars().all()

        assert len(iterations) == 1
        assert iterations[0].summary == "did stuff"
        assert len(changes) == 1
        assert changes[0].path == "app/foo.py"
        assert len(decisions) == 1
        assert decisions[0].agent == "coder"
