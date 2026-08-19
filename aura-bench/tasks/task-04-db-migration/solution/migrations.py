def get_migrations():
    """Return the ordered list of SQL statements that make up the schema."""
    return [
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
        "ALTER TABLE users ADD COLUMN email TEXT",
    ]


def apply_migrations(conn):
    cur = conn.cursor()
    for statement in get_migrations():
        cur.execute(statement)
    conn.commit()
