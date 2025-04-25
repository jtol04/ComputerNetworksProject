from flask import Flask, render_template
import requests

app = Flask(__name__)


@app.route('/')
def index():
    logs = requests.get("http://localhost:10001/logs").json()  # or use your tracker IP
    return render_template("index.html", logs=logs)


if __name__ == "__main__":
    app.run(port=8000)
