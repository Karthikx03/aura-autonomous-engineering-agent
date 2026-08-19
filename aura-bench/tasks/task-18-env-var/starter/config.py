import os


def get_database_url():
    # BUG: ignores the DATABASE_URL environment variable entirely
    return "sqlite:///default.db"
