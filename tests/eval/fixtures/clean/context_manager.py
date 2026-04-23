from contextlib import contextmanager
import time
@contextmanager
def timed():
    t0 = time.monotonic()
    try:
        yield
    finally:
        print(f"took {time.monotonic() - t0:.3f}s")
