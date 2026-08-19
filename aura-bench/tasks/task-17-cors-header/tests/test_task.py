from http_headers import build_response_headers


def test_headers_reflect_requesting_origin():
    headers = build_response_headers("https://app.example.com")
    assert headers["Access-Control-Allow-Origin"] == "https://app.example.com"


def test_headers_include_allow_methods():
    headers = build_response_headers("https://app.example.com")
    assert "Access-Control-Allow-Methods" in headers
    assert "GET" in headers["Access-Control-Allow-Methods"]
