from evens import first_n_even_numbers


def test_first_five_even_numbers():
    assert first_n_even_numbers(5) == [2, 4, 6, 8, 10]


def test_first_one_even_number():
    assert first_n_even_numbers(1) == [2]


def test_correct_count():
    assert len(first_n_even_numbers(20)) == 20
