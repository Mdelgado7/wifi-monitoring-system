import os
import time
from datetime import datetime, timezone
import threading
from flask import Flask, Response
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

app = Flask(__name__)
LOG_FILE = "/logs/metrics.log"

# --- Unified InfluxDB Configuration ---
INFLUX_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("DOCKER_INFLUXDB_INIT_ADMIN_TOKEN", "mysecrettoken123")
INFLUX_ORG = os.getenv("DOCKER_INFLUXDB_INIT_ORG", "CSUCI")
INFLUX_BUCKET = os.getenv("DOCKER_INFLUXDB_INIT_BUCKET", "WifiData")

# --- Initialize InfluxDB Client ---
try:
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    print("[*] Successfully connected to InfluxDB Client.")
except Exception as e:
    print(f"[!] Error connecting to InfluxDB: {e}")
    write_api = None

# Generate a unique Session ID for this run (Using timezone-aware UTC datetime to fix deprecation warning)
SESSION_ID = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
print(f"[*] Starting Exporter App. Active session ID: {SESSION_ID}")

def get_actual_host_cpu():
    """
    Calculates host CPU utilization % by measuring the delta 
    in /proc/stat CPU ticks over a 1-second interval.
    """
    try:
        if not os.path.exists("/proc/stat"):
            return 0.0

        def read_cpu_ticks():
            with open("/proc/stat", "r") as f:
                first_line = f.readline()
            parts = first_line.split()
            # Sum up all CPU ticks (user, nice, system, idle, iowait, irq, softirq, steal)
            ticks = [float(x) for x in parts[1:5]] # user, nice, system, idle
            total_ticks = sum(ticks)
            idle_ticks = ticks[3] # Index 3 is idle time
            return total_ticks, idle_ticks

        # Snapshot 1
        total1, idle1 = read_cpu_ticks()
        time.sleep(1.0)
        # Snapshot 2
        total2, idle2 = read_cpu_ticks()

        # Calculate the differences
        total_delta = total2 - total1
        idle_delta = idle2 - idle1

        if total_delta > 0:
            # CPU Usage = 100 * (1 - IdleDelta / TotalDelta)
            cpu_percent = (1.0 - (idle_delta / total_delta)) * 100.0
            return round(cpu_percent, 2)
    except Exception as e:
        print(f"[!] Error calculating host CPU in Python: {e}")
    return 0.0

def get_actual_host_ram():
    """
    Reads /proc/meminfo directly from the host system mount
    to calculate real physical RAM usage percentage.
    """
    try:
        if not os.path.exists("/proc/meminfo"):
            return 0.0
            
        mem_info = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    # e.g., "MemTotal: 8123456 kB" -> {'MemTotal': 8123456}
                    key = parts[0].strip(":")
                    mem_info[key] = float(parts[1])
        
        total = mem_info.get("MemTotal", 0)
        available = mem_info.get("MemAvailable", 0)
        
        if total > 0:
            # Calculate: (Total - Available) / Total * 100
            percent_used = ((total - available) / total) * 100
            return round(percent_used, 2)
    except Exception as e:
        print(f"[!] Error calculating host RAM in Python: {e}")
    return 0.0

def parse_latest():
    """
    Safely reads metrics.log and parses the latest complete block
    delineated by --- to prevent race conditions during active writes.
    """
    try:
        if not os.path.exists(LOG_FILE):
            return {}

        with open(LOG_FILE, "r") as f:
            content = f.read()

        blocks = content.strip().split('---')
        if len(blocks) < 2:
            return {}

        latest = blocks[-2].strip()
        lines = latest.split("\n")
        data = {}
        for line in lines:
            # Handle the Timestamp line formatted with a colon (Timestamp: <date>)
            if line.startswith("Timestamp:"):
                _, val = line.split(":", 1)
                data["Timestamp"] = val.strip()
            # Handle all other variables formatted with an equals sign (key=value)
            elif "=" in line:
                key, val = line.split("=", 1)
                data[key.strip()] = val.strip()
        return data
    except Exception as e:
        print(f"[!] Error parsing log boundaries: {e}")
        return {}


def safe_float(val):
    try:
        return float(val)
    except:
        return 0.0


def influx_writer_loop():
    """
    Background daemon thread that periodically writes the parsed metrics
    to InfluxDB, tagging each entry with the active Session ID.
    """
    print("[*] Background InfluxDB writer thread started.")
    last_processed_timestamp = None

    while True:
        if write_api is not None:
            data = parse_latest()
            timestamp = data.get("Timestamp")

            # Diagnostic log to trace execution in docker-compose logs
            if not timestamp:
                print("[?] Diagnostic: No timestamp found in metrics.log yet. Waiting...")

            # Check if we have a fresh block that we haven't written yet
            if timestamp and timestamp != last_processed_timestamp:
                try:
                    # Collect and sanitize network metrics
                    signal = safe_float(data.get("signal", -99))
                    ssid = data.get("ssid", "Unknown")
                    latency = safe_float(data.get("latency", 0))
                    packet_loss = safe_float(data.get("packet_loss", 0))
                    dns = safe_float(data.get("dns", 0))
                    throughput_in = safe_float(data.get("throughput_in", 0))
                    throughput_out = safe_float(data.get("throughput_out", 0))
                    link_quality = safe_float(data.get("link_quality", 0))
                    frequency = safe_float(data.get("frequency", 0))
                    bitrate = safe_float(data.get("bitrate", 0))
                    bssid = data.get("bssid", "Unknown")

                    # Pi Hardware Vitals
                    cpu_temp = safe_float(data.get("cpu_temp", 0))
                    uptime = safe_float(data.get("uptime", 0))
                    ram_usage = get_actual_host_ram()
                    cpu_usage = get_actual_host_cpu()

                    # Construct InfluxDB Point
                    point = (
                        Point("wifi_telemetry")
                        .tag("session_id", SESSION_ID)
                        .tag("ssid", ssid)
                        .tag("bssid", bssid)
                        .field("signal_dbm", signal)
                        .field("link_quality_percent", link_quality)
                        .field("frequency_mhz", frequency)
                        .field("bitrate_mbps", bitrate)
                        .field("latency_ms", latency)
                        .field("packet_loss_percent", packet_loss)
                        .field("dns_ms", dns)
                        .field("throughput_in_kbps", throughput_in)
                        .field("throughput_out_kbps", throughput_out)
                        .field("cpu_temp_celsius", cpu_temp)
                        .field("uptime_seconds", uptime)
                        .field("ram_usage_percent", ram_usage)
                        .field("cpu_usage_percent", cpu_usage)
                    )

                    write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
                    last_processed_timestamp = timestamp
                    print(f"[*] InfluxDB successfully logged data point for session {SESSION_ID} (TS: {timestamp})")
                except Exception as e:
                    print(f"[!] Background InfluxDB Write Error: {e}")

        time.sleep(2)


# --- Launch InfluxDB Writer in a Background Thread ---
bg_thread = threading.Thread(target=influx_writer_loop, daemon=True)
bg_thread.start()


# --- Flask Endpoint for Prometheus ---
@app.route("/metrics")
def metrics():
    data = parse_latest()

    signal = safe_float(data.get("signal", -99))
    latency = safe_float(data.get("latency", 0))
    packet_loss = safe_float(data.get("packet_loss", 0))
    dns = safe_float(data.get("dns", 0))
    throughput_in = safe_float(data.get("throughput_in", 0))
    throughput_out = safe_float(data.get("throughput_out", 0))

    # Pi Hardware Vitals
    cpu_temp = safe_float(data.get("cpu_temp", 0))
    uptime = safe_float(data.get("uptime", 0))
    ram_usage = get_actual_host_ram()
    cpu_usage = get_actual_host_cpu()

    output = f"""# HELP wifi_signal_dbm WiFi Signal Strength in dBm
# TYPE wifi_signal_dbm gauge
wifi_signal_dbm {signal}

# HELP wifi_latency_ms Network roundtrip latency to target
# TYPE wifi_latency_ms gauge
wifi_latency_ms {latency}

# HELP wifi_packet_loss_percent Network ping packet loss percentage
# TYPE wifi_packet_loss_percent gauge
wifi_packet_loss_percent {packet_loss}

# HELP wifi_dns_ms DNS Query resolution speed
# TYPE wifi_dns_ms gauge
wifi_dns_ms {dns}

# HELP wifi_throughput_in_kBps Inbound transfer speeds
# TYPE wifi_throughput_in_kBps gauge
wifi_throughput_in_kBps {throughput_in}

# HELP wifi_throughput_out_kBps Outbound transfer speeds
# TYPE wifi_throughput_out_kBps gauge
wifi_throughput_out_kBps {throughput_out}

# HELP pi_cpu_temp_celsius CPU Core Temperature
# TYPE pi_cpu_temp_celsius gauge
pi_cpu_temp_celsius {cpu_temp}

# HELP pi_uptime_seconds System uptime in seconds
# TYPE pi_uptime_seconds gauge
pi_uptime_seconds {uptime}

# HELP pi_ram_usage_percent Memory utilization percentage
# TYPE pi_ram_usage_percent gauge
pi_ram_usage_percent {ram_usage}

# HELP pi_cpu_usage_percent CPU core load utilization percentage
# TYPE pi_cpu_usage_percent gauge
pi_cpu_usage_percent {cpu_usage}
"""
    return Response(output, mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
