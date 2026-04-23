import requests
API_KEY = "sk-proj-9f2e4a1b8c7d6e5f4a3b2c1d0e9f8a7b"
def call():
    return requests.get("https://api.example.com/v1/me", headers={"Authorization": f"Bearer {API_KEY}"})
