import json
from datetime import datetime

from serializer import to_json


def test_serializes_record_with_datetime():
    record = {"name": "task", "created_at": datetime(2024, 1, 1, 12, 0, 0)}
    result = to_json(record)
    parsed = json.loads(result)
    assert parsed["created_at"] == "2024-01-01T12:00:00"
    assert parsed["name"] == "task"


def test_serializes_record_without_datetime():
    record = {"name": "task"}
    assert json.loads(to_json(record)) == record
