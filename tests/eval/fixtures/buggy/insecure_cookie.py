from flask import Flask, make_response
app = Flask(__name__)
@app.route("/login")
def login():
    resp = make_response("ok")
    resp.set_cookie("session", "abc123")  # no secure/httponly/samesite
    return resp
