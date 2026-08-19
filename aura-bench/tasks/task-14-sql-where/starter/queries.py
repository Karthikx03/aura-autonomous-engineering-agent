def get_active_users(conn):
    cur = conn.cursor()
    # BUG: missing WHERE active = 1, returns every user regardless of status
    cur.execute("SELECT id, name FROM users")
    return cur.fetchall()
