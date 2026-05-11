#!/bin/bash

# Verify Installation of stress-ng
if ! command -v stress-ng &> /dev/null; then
	echo "stress-ng is not installed, Installing it now..."
	sudo apt update && sudo apt install -y stress-ng
fi

# CPU Spike
echo "Starting.. Spiking CPU (4 cores @ 100%) for 20 seconds"
stress-ng --cpu 4 --timeout 20s
echo "--> CPU Spike Completed."

# Delay
sleep 5

# RAM Spike
echo "--> Spiking RAM (1GB  allocation) for 30 seconds"
stress-ng --vm 2 --vm-bytes 2G --timeout 20s
echo "--> RAM Spike Completed."

echo "==================================================="
echo "# Test Complete! Check your feels good dashboard! #"
echo "==================================================="
