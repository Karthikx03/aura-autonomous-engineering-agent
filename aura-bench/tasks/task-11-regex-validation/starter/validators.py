import re

# BUG: the '.' before \w+ is unescaped, so it matches ANY character, not
# just a literal dot. This lets domains with no real dot validate.
EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+.\w+$")


def validate_email(value):
    return bool(EMAIL_PATTERN.match(value))
