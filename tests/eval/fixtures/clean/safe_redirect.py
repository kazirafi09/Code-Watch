from urllib.parse import urlparse
from flask import Flask, request, redirect, abort
app = Flask(__name__)
ALLOWED = {"example.com", "www.example.com"}
@app.route("/go")
def go():
    target = request.args["next"]
    if urlparse(target).hostname not in ALLOWED:
        abort(400)
    return redirect(target)
