ITEMS = []


def list_items(body=None):
    return {"status": 200, "body": list(ITEMS)}


# BUG: no handler exists for creating items, so POST /items is unregistered
HANDLERS = {
    ("GET", "/items"): list_items,
}


def dispatch(method, path, body=None):
    handler = HANDLERS.get((method, path))
    if handler is None:
        return {"status": 404, "body": "Not Found"}
    return handler(body)
