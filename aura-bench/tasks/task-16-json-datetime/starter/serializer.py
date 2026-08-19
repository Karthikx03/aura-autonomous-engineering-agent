import json


def to_json(record):
    # BUG: raises TypeError when record contains a datetime value, since
    # datetime is not JSON serializable by default.
    return json.dumps(record)
