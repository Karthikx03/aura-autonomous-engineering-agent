def paginate(items, page, page_size):
    """Return the 0-indexed page of items, page_size items per page."""
    start = page * page_size
    # BUG: off-by-one drops the last item of every page
    end = start + page_size - 1
    return items[start:end]
