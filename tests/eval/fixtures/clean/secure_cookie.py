from flask import Flask, make_response
app = Flask(__name__)
@app.route("/login")
def login():
    r = make_response("ok")
    r.set_cookie("session", "abc123", secure=True, httponly=True, samesite="Lax")
    return r
