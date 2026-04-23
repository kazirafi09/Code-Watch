import pickle
from pathlib import Path
LOCAL_CACHE = Path("/var/app/cache.bin")
def load_local():
    # Local, application-controlled file; not from network.
    with LOCAL_CACHE.open("rb") as f:
        return pickle.load(f)
