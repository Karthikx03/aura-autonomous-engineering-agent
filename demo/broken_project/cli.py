"""Tiny CLI wrapper around tasklist.TaskList (pure standard library).

Usage:
    python3 cli.py

This just seeds a couple of tasks and prints a summary, so the module is
runnable end to end without any dependencies. It is not covered directly
by tests/ - tests exercise TaskList itself.
"""

from tasklist import TaskList


def main():
    tasks = TaskList()
    tasks.add("Write the report")
    tasks.add("Review pull request")
    tasks.add("Deploy to staging")
    tasks.complete(1)

    summary = tasks.summary()
    print(f"Total tasks:   {summary['total']}")
    print(f"Done:          {summary['done']}")
    print(f"Pending:       {summary['pending']}")
    for task in tasks.pending():
        print(f"  - [ ] {task['title']}")


if __name__ == "__main__":
    main()
