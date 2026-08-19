def paginate(items, page, page_size):
    """Return the 0-indexed page of items, page_size items per page."""
    start = page * page_size
    end = start + page_size
    return items[start:end]
