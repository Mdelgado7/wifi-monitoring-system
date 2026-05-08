import os
import time
from datetime import datetime
import threading
from flask import Flask, Response
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)
LOG_FILE = "/logs/metrics.log"

# --- InfluxDB Configuration ---
# Pull credentials directly from the environment variables set in docker-compose
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", "mysecrettoken123")
INFLUX_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG", "CSUCI")
INFLUX_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET", "WifiData")

# Initialize InfluxDB Client
influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

# Generate a unique Session ID for this run (survives power down/up as separate runs)
SESSION_ID = f"session_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
print(f"[*] Starting new telemetry session: {SESSION_ID}")

def parse_latest():
    try:
        if not os.path.exists(LOG_FILE):
            return {}
            
        with open(LOG_FILE, "r") as f:
            content = f.read()

        # Split into blocks based on '---'
        blocks = [b.strip() for b in content.split('---') if b.strip()]
        if not blocks:
            return {}

        # Get the absolute latest complete block
        latest = blocks[-1]
        lines = latest.split("\n")
        data = {}
        for line in lines:
            if "=" in line:
                key, val = line.split("=", 1)
                data[key.strip()] = val.strip()
            elif "Timestamp:" in line:
                data["Timestamp"] = line.replace("Timestamp:", "").strip()
        return data
    except Exception as e:
        print("ERROR PARSING LOGS:", e)
        return {}

def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0

# --- Background Worker to write to InfluxDB ---
def influx_writer_loop():
    """Continuously checks for new entries and writes them permanently to InfluxDB"""
    print("[*] InfluxDB Writer Thread Started.")
    last_processed_time = None

    while True:
        try:
            data = parse_latest()
            if data and "Timestamp" in data:
                current_time_str = data["Timestamp"]

                # Only write to InfluxDB if it's a brand new timestamp block
                if current_time_str != last_processed_time:
                    signal = safe_float(data.get("signal", 0))
                    latency = safe_float(data.get("latency", 0))
                    dns = safe_float(data.get("dns", 0))
                    throughput_in = safe_float(data.get("throughput_in", 0))
                    throughput_out = safe_float(data.get("throughput_out", 0))
                    ssid = data.get("ssid", "Unknown")

                    # Construct InfluxDB Point
                    point = (
                        Point("wifi_telemetry")
                        .tag("session_id", SESSION_ID)  # Segmentation Tag!
                        .tag("ssid", ssid)
                        .field("signal_dbm", signal)
                        .field("latency_ms", latency)
                        .field("dns_ms", dns)
                        .field("throughput_in_kbps", throughput_in)
                        .field("throughput_out_kbps", throughput_out)
                        .time(datetime.utcnow(), WritePrecision.NS)
                    )

                    # Write to database
                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    print(f"[InfluxDB] Saved point for {SESSION_ID} ({current_time_str})")
                    
                    last_processed_time = current_time_str
        except Exception as e:
            print("[InfluxDB Error]:", e)
        
        time.sleep(2)  # Check for new data every 2 seconds


# Start InfluxDB writing process in a separate non-blocking thread
threading.Thread(target=influx_writer_loop, daemon=True).start()

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
