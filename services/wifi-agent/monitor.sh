#!/bin/bash
INTERFACE=${INTERFACE:-wlan0}
TARGET=${TARGET:-8.8.8.8}
LOG_FILE="/logs/metrics.log"

echo "Starting WiFi Monitoring on $INTERFACE..."
mkdir -p /var/lib/vnstat
vnstat -u -i $INTERFACE 2>/dev/null
vnstatd -n &
sleep 2

# Ensure log directory and file exist
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

# Initialize persistence variables
LAST_GOOD_SIGNAL="-50"      # Standard starting baseline
LAST_GOOD_SSID="Searching"

while true
do
    TIMESTAMP=$(date)
    
    # 1. Capture the raw link status once to avoid double-querying the hardware
    LINK_STATUS=$(iw dev $INTERFACE link 2>/dev/null)

    # 2. Extract metrics safely from the single capture
    CURRENT_SIGNAL=$(echo "$LINK_STATUS" | grep signal | awk '{print $2}')
    CURRENT_SSID=$(echo "$LINK_STATUS" | grep SSID | cut -d ':' -f2 | sed 's/^[ \t]*//')

    # 3. Apply Cache Protection: If raw capture fails, use the last known good data
    if [ -n "$CURRENT_SIGNAL" ] && [ "$CURRENT_SIGNAL" != "0" ]; then
        LAST_GOOD_SIGNAL="$CURRENT_SIGNAL"
    fi

    if [ -n "$CURRENT_SSID" ] && [ "$CURRENT_SSID" != "Not connected." ]; then
        LAST_GOOD_SSID="$CURRENT_SSID"
    fi

    # 4. Standard metric lookups
    LATENCY=$(ping -c 1 $TARGET 2>/dev/null | tail -1 | awk -F'/' '{print $5}')
    DNS=$(dig google.com 2>/dev/null | grep 'Query time' | awk '{print $4}')
    GATEWAY=$(ip route 2>/dev/null | grep default | awk '{print $3}')
    
    # Live throughput (in KB/s)
    read in out <<< $(ifstat -i $INTERFACE 1 1 | tail -1 | awk '{print $1, $2}')

    # Apply defaults to other network metrics if they timeout
    LATENCY=${LATENCY:-0}
    DNS=${DNS:-0}
    GATEWAY=${GATEWAY:-"0.0.0.0"}
    in=${in:-0}
    out=${out:-0}

    # Write formatted block using the protected variables
    {
        echo "---"
        echo "Timestamp: $TIMESTAMP"
        echo "signal=$LAST_GOOD_SIGNAL"
        echo "ssid=$LAST_GOOD_SSID"
        echo "latency=$LATENCY"
        echo "dns=$DNS"
        echo "gateway=$GATEWAY"
        echo "throughput_in=$in"
        echo "throughput_out=$out"
    } >> "$LOG_FILE"

    sleep 5
done
