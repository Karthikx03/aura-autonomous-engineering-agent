def get_active_users(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE active = 1")
    return cur.fetchall()
