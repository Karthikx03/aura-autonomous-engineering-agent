import sqlite3

from queries import get_active_users


def _make_conn():
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, active INTEGER)")
    cur.executemany(
        "INSERT INTO users (name, active) VALUES (?, ?)",
        [("alice", 1), ("bob", 1), ("carol", 0)],
    )
    conn.commit()
    return conn


def test_only_active_users_returned():
    conn = _make_conn()
    rows = get_active_users(conn)
    assert len(rows) == 2
    conn.close()


def test_inactive_user_excluded():
    conn = _make_conn()
    rows = get_active_users(conn)
    names = {row[1] for row in rows}
    assert "carol" not in names
    conn.close()
