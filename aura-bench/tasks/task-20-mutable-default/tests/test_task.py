from todo import add_item


def test_calls_without_explicit_list_do_not_share_state():
    result1 = add_item("buy milk")
    result2 = add_item("walk dog")
    assert result1 == ["buy milk"]
    assert result2 == ["walk dog"]


def test_explicit_list_is_used_and_mutated():
    my_list = []
    result = add_item("task", my_list)
    assert result is my_list
    assert result == ["task"]
