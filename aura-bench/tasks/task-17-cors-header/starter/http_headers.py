def build_response_headers(origin):
    # BUG: ignores the actual request origin, hardcodes it, and is missing
    # the Access-Control-Allow-Methods header entirely.
    return {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "http://localhost:3000",
    }
