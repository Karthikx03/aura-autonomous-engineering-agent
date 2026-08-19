import json
from datetime import datetime


def _default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def to_json(record):
    return json.dumps(record, default=_default)
