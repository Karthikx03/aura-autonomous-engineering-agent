from auth import login

USERS_DB = {"alice": "correct-horse-battery-staple"}


def test_correct_password_grants_access():
    assert login("alice", "correct-horse-battery-staple", USERS_DB) is True


def test_wrong_password_denies_access():
    assert login("alice", "wrong-password", USERS_DB) is False


def test_unknown_user_denies_access():
    assert login("bob", "anything", USERS_DB) is False
