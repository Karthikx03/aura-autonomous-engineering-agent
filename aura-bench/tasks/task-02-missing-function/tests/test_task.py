from string_utils import reverse_words


def test_reverse_words_basic():
    assert reverse_words("hello world") == "world hello"


def test_reverse_words_collapses_whitespace():
    assert reverse_words("  a   b  c ") == "c b a"


def test_reverse_words_single_word():
    assert reverse_words("solo") == "solo"
