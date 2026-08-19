import time


class Counter:
    def __init__(self):
        self.value = 0

    def increment(self):
        # BUG: not thread-safe - read/modify/write is not atomic. The
        # time.sleep(0) below only exists to make the race reliably
        # observable in a fast unit test by widening the window between
        # the read and the write; the real bug is the missing lock around
        # that read/modify/write sequence.
        current = self.value
        time.sleep(0)
        current += 1
        self.value = current


def run_increments(counter, times):
    for _ in range(times):
        counter.increment()
