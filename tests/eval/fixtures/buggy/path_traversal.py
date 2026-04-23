from flask import Flask, request
app = Flask(__name__)
@app.route("/read")
def read():
    name = request.args["f"]
    with open("/var/data/" + name) as fh:
        return fh.read()
