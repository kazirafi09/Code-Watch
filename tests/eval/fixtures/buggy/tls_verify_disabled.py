import requests
def charge(card):
    return requests.post("https://pay.example.com/charge", json=card, verify=False)
