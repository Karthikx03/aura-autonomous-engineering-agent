import sqlite3

from migrations import apply_migrations


def test_users_table_has_email_column():
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cur.fetchall()}
    assert "email" in columns
    conn.close()


def test_users_table_still_has_original_columns():
    conn = sqlite3.connect(":memory:")
    apply_migrations(conn)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(users)")
    columns = {row[1] for row in cur.fetchall()}
    assert {"id", "name"}.issubset(columns)
    conn.close()
