def call_with_retry(fn, max_attempts=3):
    # BUG: max_attempts is accepted but never enforced - this loops
    # unboundedly until fn() succeeds, with no backoff or give-up path.
    while True:
        try:
            return fn()
        except Exception:
            continue
