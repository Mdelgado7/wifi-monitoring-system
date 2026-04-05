from flask import Flask, Response

app = Flask(__name__)

LOG_FILE = "/logs/metrics.log"


def parse_latest():
    try:
        with open(LOG_FILE, "r") as f:
            content = f.read()

        # Split into blocks
        blocks = content.strip().split('---')

        # Get the last FULL block (ignore trailing empty)
        latest = blocks[-2].strip() if len(blocks) > 1 else ""

        lines = latest.split("\n")

        data = {}
        for line in lines:
            if "=" in line:
                key, val = line.split("=", 1)
                data[key.strip()] = val.strip()

        print("PARSED BLOCK:", latest)
        print("PARSED DATA:", data)

        return data

    except Exception as e:
        print("ERROR:", e)
        return {}

def safe_float(val):
    try:
        return float(val)
    except:
        return 0

@app.route("/metrics")
def metrics():
    data = parse_latest()

    signal = safe_float(data.get("signal", 0))
    latency = safe_float(data.get("latency", 0))
    dns = safe_float(data.get("dns", 0))
    throughput_in = safe_float(data.get("throughput_in", 0))
    throughput_out = safe_float(data.get("throughput_out", 0))

    output = f"""
wifi_signal_dbm {signal}

wifi_latency_ms {latency}

wifi_dns_ms {dns}

wifi_throughput_in_kBps {throughput_in}

wifi_throughput_out_kBps {throughput_out}
"""

    return Response(output, mimetype="text/plain")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
