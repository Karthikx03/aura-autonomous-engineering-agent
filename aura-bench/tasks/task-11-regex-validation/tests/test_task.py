from validators import validate_email


def test_valid_email_accepted():
    assert validate_email("user@example.com") is True


def test_domain_without_literal_dot_is_rejected():
    # Under the buggy pattern the unescaped '.' matches any character,
    # so this string with no real dot incorrectly validates.
    assert validate_email("bob@sitexcom") is False


def test_missing_at_sign_is_rejected():
    assert validate_email("not-an-email.com") is False
