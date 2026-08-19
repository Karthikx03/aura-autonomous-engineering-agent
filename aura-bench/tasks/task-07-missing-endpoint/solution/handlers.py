ITEMS = []


def list_items(body=None):
    return {"status": 200, "body": list(ITEMS)}


def create_item(body=None):
    item = body or {}
    ITEMS.append(item)
    return {"status": 201, "body": item}


HANDLERS = {
    ("GET", "/items"): list_items,
    ("POST", "/items"): create_item,
}


def dispatch(method, path, body=None):
    handler = HANDLERS.get((method, path))
    if handler is None:
        return {"status": 404, "body": "Not Found"}
    return handler(body)
