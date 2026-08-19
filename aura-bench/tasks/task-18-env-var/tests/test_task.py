from config import get_database_url


def test_reads_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://example/db")
    assert get_database_url() == "postgres://example/db"


def test_falls_back_to_default_when_unset(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert get_database_url() == "sqlite:///default.db"
