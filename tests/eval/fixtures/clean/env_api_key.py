import os, requests
def call():
    key = os.environ["API_KEY"]
    return requests.get("https://api.example.com/v1/me", headers={"Authorization": f"Bearer {key}"})
