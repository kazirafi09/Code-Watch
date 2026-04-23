import requests
def fetch(url):
    return requests.get(url).text
def handler(req):
    return fetch(req.params["u"])
