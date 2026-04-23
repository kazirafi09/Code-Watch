import subprocess
def ping(host: str):
    subprocess.run(["ping", "-c", "1", host], check=True)
