from consumer import compute


def test_compute_uses_add_and_multiply():
    # (2 + 3) * (2 * 3) = 5 * 6 = 30
    assert compute(2, 3) == 30


def test_compute_with_zero():
    assert compute(0, 5) == 0
