import os
def safe_write(path, data):
    if not os.path.exists(path):
        with open(path, "w") as f:  # TOCTOU race
            f.write(data)
