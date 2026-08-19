from retry import call_with_retry


class _GuardExceeded(BaseException):
    """Raised (as a BaseException, not Exception) when a retry loop has
    clearly gone unbounded, so a buggy implementation that only catches
    Exception can't swallow it and hang the test suite forever."""


def _make_always_failing_fn(guard_after=50):
    state = {"calls": 0}

    def fn():
        state["calls"] += 1
        if state["calls"] > guard_after:
            raise _GuardExceeded(
                f"call_with_retry invoked fn more than {guard_after} times - "
                "looks like max_attempts is not being enforced"
            )
        raise ValueError("simulated persistent failure")

    return fn, state


def test_retry_succeeds_before_exhausting_attempts():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient failure")
        return "ok"

    assert call_with_retry(flaky, max_attempts=5) == "ok"


def test_retry_gives_up_after_max_attempts():
    fn, state = _make_always_failing_fn(guard_after=50)
    result = call_with_retry(fn, max_attempts=5)
    assert isinstance(result, dict)
    assert result["success"] is False
    assert result["attempts"] == 5
    assert state["calls"] == 5
