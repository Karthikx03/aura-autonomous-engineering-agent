import threading

from counter import Counter, run_increments


def test_counter_is_thread_safe():
    counter = Counter()
    n_threads = 20
    increments_per_thread = 50
    threads = [
        threading.Thread(target=run_increments, args=(counter, increments_per_thread))
        for _ in range(n_threads)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert counter.value == n_threads * increments_per_thread
