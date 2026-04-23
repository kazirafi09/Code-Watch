from flask import Flask, render_template, request
app = Flask(__name__)
@app.route("/hi")
def hi():
    return render_template("hi.html", name=request.args.get("name", ""))
