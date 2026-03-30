#!/bin/bash

INTERFACE=${INTERFACE:-wlan0}
TARGET=${TARGET:-8.8.8.8}
LOG_FILE="/logs/metrics.log"

echo "Starting WiFi Monitoring on $INTERFACE..."

mkdir -p /var/lib/vnstat
vnstat --add -i $INTERFACE 2>/dev/null
vnstatd -n &

sleep 2

while true
do
    {
        echo "Timestamp: $(date)"

        echo "signal=$(iw dev $INTERFACE link 2>/dev/null | grep signal | awk '{print $2}')"
        echo "ssid=$(iw dev $INTERFACE link 2>/dev/null | grep SSID | cut -d ':' -f2)"

        echo "latency=$(ping -c 1 $TARGET | tail -1 | awk -F'/' '{print $5}')"

        echo "dns=$(dig google.com | grep 'Query time' | awk '{print $4}')"

        echo "gateway=$(ip route | grep default | awk '{print $3}')"

        echo "throughput=$(ifstat -i $INTERFACE 1 1 | tail -1 | awk '{print $1}')"

        echo "---"
    } >> $LOG_FILE

    sleep 5
done
