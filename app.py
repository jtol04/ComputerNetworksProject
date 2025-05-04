from global_vars import TRACKER_PORT
from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def whiteboard():
    return render_template("whiteboard.html")


@app.route('/chains')
def get_chains():
    chains = requests.get("http://localhost:9000/chains").json()
    return jsonify(chains)


if __name__ == "__main__":
    app.run(port=8000)
