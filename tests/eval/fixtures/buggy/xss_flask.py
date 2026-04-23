from flask import Flask, request
from markupsafe import Markup
app = Flask(__name__)
@app.route("/hi")
def hi():
    return Markup("<h1>Hello " + request.args.get("name", "") + "</h1>")
