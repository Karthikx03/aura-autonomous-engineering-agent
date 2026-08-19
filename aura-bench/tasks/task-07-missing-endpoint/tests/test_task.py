import handlers


def setup_function(_fn):
    handlers.ITEMS.clear()


def test_create_item_returns_201():
    resp = handlers.dispatch("POST", "/items", {"name": "widget"})
    assert resp["status"] == 201
    assert resp["body"] == {"name": "widget"}


def test_created_item_shows_up_in_list():
    handlers.dispatch("POST", "/items", {"name": "widget"})
    resp = handlers.dispatch("GET", "/items")
    assert resp["status"] == 200
    assert resp["body"] == [{"name": "widget"}]
