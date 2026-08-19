def reverse_words(s):
    """Reverse the order of words in a whitespace-separated string."""
    return " ".join(s.split()[::-1])
