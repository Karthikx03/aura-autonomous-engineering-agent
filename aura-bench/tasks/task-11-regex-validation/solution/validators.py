import re

EMAIL_PATTERN = re.compile(r"^[\w.+-]+@[\w-]+\.[A-Za-z]{2,}$")


def validate_email(value):
    return bool(EMAIL_PATTERN.match(value))
