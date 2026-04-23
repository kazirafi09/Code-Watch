import subprocess
def ping(host):
    subprocess.run(f"ping -c 1 {host}", shell=True)
