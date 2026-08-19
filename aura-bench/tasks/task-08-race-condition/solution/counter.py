import threading
import time


class Counter:
    def __init__(self):
        self.value = 0
        self._lock = threading.Lock()

    def increment(self):
        with self._lock:
            current = self.value
            time.sleep(0)
            current += 1
            self.value = current


def run_increments(counter, times):
    for _ in range(times):
        counter.increment()
