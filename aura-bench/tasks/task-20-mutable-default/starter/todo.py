def add_item(item, items=[]):
    # BUG: mutable default argument is shared and reused across calls
    items.append(item)
    return items
