#!/bin/bash
INTERFACE=${INTERFACE:-wlan0}
TARGET=${TARGET:-8.8.8.8}
LOG_FILE="/logs/metrics.log"

echo "Starting Enhanced WiFi & System Monitoring on $INTERFACE..."
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Initialize vnstat if needed
if ! vnstat --dbdir /var/lib/vnstat -i "$INTERFACE" >/dev/null 2>&1; then
    vnstat --dbdir /var/lib/vnstat --add -i "$INTERFACE"
fi

# Track last good values to prevent empty scraping race conditions
LAST_GOOD_SSID="Unknown"
LAST_GOOD_SIGNAL="-99"

while true
do
    {
        echo "Timestamp: $(date)"
        
        # 1. WiFi Connections Stats
        LINK_STATUS=$(iw dev "$INTERFACE" link 2>/dev/null)
        if echo "$LINK_STATUS" | grep -q "Connected"; then
            SIGNAL=$(echo "$LINK_STATUS" | grep signal | awk '{print $2}')
            SSID=$(echo "$LINK_STATUS" | grep SSID | cut -d ':' -f2 | sed 's/^[ \t]*//')
            LAST_GOOD_SIGNAL=$SIGNAL
            LAST_GOOD_SSID=$SSID
        else
            SIGNAL=$LAST_GOOD_SIGNAL
            SSID=$LAST_GOOD_SSID
        fi
        echo "signal=$SIGNAL"
        echo "ssid=$SSID"

        # 2. Latency & Packet Loss (Using ping)
        PING_OUT=$(ping -c 3 "$TARGET" 2>/dev/null)
        LATENCY=$(echo "$PING_OUT" | tail -1 | awk -F'/' '{print $5}')
        # Parse packet loss percentage
        PACKET_LOSS=$(echo "$PING_OUT" | grep -oP '\d+(?=% packet loss)')
        
        echo "latency=${LATENCY:-0}"
        echo "packet_loss=${PACKET_LOSS:-0}"

        # 3. DNS Lookup Times
        DNS_TIME=$(dig @1.1.1.1 google.com | grep 'Query time' | awk '{print $4}')
        echo "dns=${DNS_TIME:-0}"

        # 4. Network Throughput (using ifstat)
        read in out <<< $(ifstat -i "$INTERFACE" 1 1 | tail -1 | awk '{print $1, $2}')
        echo "throughput_in=${in:-0}"
        echo "throughput_out=${out:-0}"

        # 5. System Performance Vitals (Pi 5 Specific)
        # CPU Temperature (scaled down to Celsius degrees)
        if [ -f /sys/class/thermal/thermal_zone0/temp ]; then
            CPU_TEMP=$(awk '{print $1/1000}' /sys/class/thermal/thermal_zone0/temp)
        else
            CPU_TEMP=0
        fi
        # System Uptime (seconds)
        UPTIME=$(awk '{print $1}' /proc/uptime)
	
	# We will let app.py calculate the memory directly to bypass container shells
	echo "ram_usage=DELEGATED"
	
	LINK_QUALITY=$(awk '/wlan0/ {print int($3)}' /proc/net/wireless)
	echo "link_quality=${LINK_QUALITY:-0}"

	# Grab the active frequency in MHz (e.g., 5240 or 2412)
	FREQ=$(iw dev "$INTERFACE" link | grep "freq:" | awk '{print $2}')
	echo "frequency=${FREQ:-0}"

	# Grab tx bitrate (e.g., 150.0 MBit/s -> 150)
	BITRATE=$(iw dev "$INTERFACE" link | grep "tx bitrate" | awk '{print $3}' | cut -d'.' -f1)
	echo "bitrate=${BITRATE:-0}"

	BSSID=$(iw dev "$INTERFACE" link | grep "Connected to" | awk '{print $3}')
	echo "bssid=${BSSID:-Unknown}"

        echo "cpu_temp=${CPU_TEMP}"
        echo "uptime=${UPTIME}"
        echo "ram_usage=${RAM_USAGE}"
        echo "---"
    } >> "$LOG_FILE"
    
    sleep 5
done
