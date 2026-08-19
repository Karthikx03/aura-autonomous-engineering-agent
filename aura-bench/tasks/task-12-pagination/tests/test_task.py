from pagination import paginate

ITEMS = list(range(10))


def test_first_page_has_full_page_size():
    assert paginate(ITEMS, 0, 5) == [0, 1, 2, 3, 4]


def test_second_page_has_full_page_size():
    assert paginate(ITEMS, 1, 5) == [5, 6, 7, 8, 9]


def test_partial_last_page():
    assert paginate(ITEMS, 0, 3) == [0, 1, 2]
