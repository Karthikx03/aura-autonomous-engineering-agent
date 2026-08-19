"""A tiny in-memory task list manager (pure standard library).

This is the core module used by cli.py. It intentionally ships with ONE
bug for the AURA demo (see FIX.md in this directory for the exact fix).
"""


class TaskList:
    def __init__(self):
        self._tasks = []
        self._next_id = 1

    def add(self, title):
        """Add a new pending task and return it."""
        task = {"id": self._next_id, "title": title, "done": False}
        self._tasks.append(task)
        self._next_id += 1
        return task

    def complete(self, task_id):
        """Mark a task as done and return it."""
        for task in self._tasks:
            if task["id"] == task_id:
                task["done"] = True
                return task
        raise KeyError(f"No task with id {task_id}")

    def pending(self):
        """Return the tasks that are not yet done."""
        return [t for t in self._tasks if not t["done"]]

    def all_tasks(self):
        """Return every task, done or not."""
        return list(self._tasks)

    def summary(self):
        """Return {'total': int, 'done': int, 'pending': int} counts."""
        total = len(self._tasks)
        done = sum(1 for t in self._tasks if t["done"])
        # BUG: off-by-one - subtracts an extra 1, so pending is undercounted
        # by one whenever there is at least one pending task.
        pending = total - done - 1
        return {"total": total, "done": done, "pending": pending}
