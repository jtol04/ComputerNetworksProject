"""
app.py

Flask application for the Rock-Paper-Scissors blockchain project UI.
Provides a whiteboard page and a JSON endpoint for blockchains.
"""
import requests
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route('/')
def whiteboard():
    """
    Render the whiteboard UI template.
    """
    return render_template("whiteboard.html")


@app.route('/chains')
def get_chains():
    """
    Fetch the current chains from the tracker and return them as JSON.
    """
    chains = requests.get("http://localhost:9000/chains").json()
    return jsonify(chains)


if __name__ == "__main__":
    app.run(port=8000)
