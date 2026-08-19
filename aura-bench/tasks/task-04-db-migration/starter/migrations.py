def get_migrations():
    """Return the ordered list of SQL statements that make up the schema."""
    return [
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)",
        # BUG: missing migration to add the 'email' column required downstream
    ]


def apply_migrations(conn):
    cur = conn.cursor()
    for statement in get_migrations():
        cur.execute(statement)
    conn.commit()
