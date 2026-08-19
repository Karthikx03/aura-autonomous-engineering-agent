from cache_store import UserStore


def test_get_user_reflects_latest_update():
    store = UserStore()
    store.set_user(1, "Alice")
    assert store.get_user(1) == "Alice"  # populates the cache

    store.set_user(1, "Alicia")
    assert store.get_user(1) == "Alicia"  # must not be stale


def test_get_user_without_prior_cache_hit():
    store = UserStore()
    store.set_user(2, "Bob")
    store.set_user(2, "Bobby")
    assert store.get_user(2) == "Bobby"
