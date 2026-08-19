def login(username, password, users_db):
    """Return True if username/password is a valid combination."""
    if username not in users_db:
        return False
    stored_password = users_db[username]
    return stored_password == password
