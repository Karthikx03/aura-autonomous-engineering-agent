def parse_int(value):
    return int(value)


def safe_parse(value):
    # BUG: lets ValueError/TypeError from parse_int propagate instead of
    # returning a structured error result.
    return {"success": True, "value": parse_int(value)}
