def call_with_retry(fn, max_attempts=3):
    attempts = 0
    last_error = None
    while attempts < max_attempts:
        attempts += 1
        try:
            return fn()
        except Exception as exc:
            last_error = exc
    return {"success": False, "attempts": attempts, "error": str(last_error)}
