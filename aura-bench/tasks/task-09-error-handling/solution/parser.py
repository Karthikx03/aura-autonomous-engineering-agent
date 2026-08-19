def parse_int(value):
    return int(value)


def safe_parse(value):
    try:
        return {"success": True, "value": parse_int(value)}
    except (ValueError, TypeError) as exc:
        return {"success": False, "error": str(exc)}
