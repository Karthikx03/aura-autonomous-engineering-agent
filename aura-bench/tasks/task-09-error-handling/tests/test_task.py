from parser import safe_parse


def test_safe_parse_valid_string():
    assert safe_parse("42") == {"success": True, "value": 42}


def test_safe_parse_invalid_string_returns_error_dict():
    result = safe_parse("not-a-number")
    assert result["success"] is False
    assert "error" in result


def test_safe_parse_none_returns_error_dict():
    result = safe_parse(None)
    assert result["success"] is False
    assert "error" in result
