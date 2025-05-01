from global_vars import TRACKER_PORT
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)


@app.route('/')
def index():
    logs = requests.get("http://localhost:9000/logs").json()
    return render_template("index.html", logs=logs)

@app.route('/whiteboard')
def whiteboard():
    return render_template("whiteboard.html")
@app.route('/chains')
def get_chains():
    chains = requests.get("http://localhost:9000/chains").json()
    return jsonify(chains)

if __name__ == "__main__":
    app.run(port=8000)
