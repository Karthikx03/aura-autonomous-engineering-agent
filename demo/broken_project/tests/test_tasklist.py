from tasklist import TaskList


def test_summary_counts_are_consistent():
    tasks = TaskList()
    tasks.add("a")
    tasks.add("b")
    tasks.add("c")
    tasks.complete(1)

    summary = tasks.summary()
    assert summary["total"] == 3
    assert summary["done"] == 1
    assert summary["pending"] == 2


def test_pending_matches_summary_pending_count():
    tasks = TaskList()
    tasks.add("a")
    tasks.add("b")

    summary = tasks.summary()
    assert summary["pending"] == len(tasks.pending())


def test_summary_with_no_tasks():
    tasks = TaskList()
    summary = tasks.summary()
    assert summary == {"total": 0, "done": 0, "pending": 0}


def test_complete_unknown_task_raises():
    tasks = TaskList()
    try:
        tasks.complete(999)
        assert False, "expected KeyError"
    except KeyError:
        pass
