class Router:
    def __init__(self):
        self.routes = {}

    def add_route(self, path, handler):
        self.routes[path] = handler

    def dispatch(self, path):
        if path not in self.routes:
            return {"status": 404, "body": "Not Found"}
        return {"status": 200, "body": self.routes[path]()}


def health_handler():
    return "ok"


def users_handler():
    return "users list"


def build_app():
    router = Router()
    router.add_route("/health", health_handler)
    router.add_route("/users", users_handler)
    return router
