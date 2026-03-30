from flask import Flask, jsonify

app = Flask(__name__)

LOG_FILE = "/logs/metrics.log"

def parse_latest():
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()

        # Get last block
        block = []
        for line in reversed(lines):
            if line.strip() == "---":
                break
            block.append(line.strip())

        block.reverse()

        data = {}
        for line in block:
            if "=" in line:
                key, val = line.split("=", 1)
                data[key] = val.strip()

        return data

    except:
        return {"error": "no data yet"}

@app.route("/metrics")
def metrics():
    return jsonify(parse_latest())

app.run(host="0.0.0.0", port=8000)
