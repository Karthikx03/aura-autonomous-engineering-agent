from router import build_app


def test_users_route_registered():
    app = build_app()
    resp = app.dispatch("/users")
    assert resp["status"] == 200
    assert resp["body"] == "users list"


def test_health_route_still_works():
    app = build_app()
    resp = app.dispatch("/health")
    assert resp["status"] == 200
    assert resp["body"] == "ok"


def test_unknown_route_is_404():
    app = build_app()
    resp = app.dispatch("/nope")
    assert resp["status"] == 404
