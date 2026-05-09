========================================================================
# README.txt
# Authors: Martin Delgado & Izzy Garcia
# Capstone Project: Multi-Point Wi-Fi Monitoring and Spatial Heat-Mapping System
# Description: This git repository hosts the docker configurations and 
#              docker compose files to create the project environment. 
#              The software used are the following: Grafana, InfluxDB, 
#              Docker, and Python data collection scripts.
========================================================================

--- Prerequisites ---
Before cloning and running this project, you must have Docker and Docker 
Compose installed on your Raspberry Pi. 

If you do not have Docker set up yet, follow our Pi setup guide for Debian machines here:
https://docs.docker.com/engine/install/debian/

--- Step 1: Clone the Repository ---
Open a terminal on your Raspberry Pi and run the following commands to 
download the project and navigate into the project root directory:

  git clone https://github.com/Mdelgado7/wifi-monitoring-system.git
  cd wifi-monitoring-system


--- Step 2: Build and Run the Docker Containers ---
Build the custom Python script images and spin up the entire monitoring 
stack (Grafana, InfluxDB, and pipeline containers) in detached mode:

  sudo docker compose build --no-cache
  sudo docker compose up -d


--- Step 3: Verify the Services are Running ---
To confirm all containers have successfully started and are running cleanly:

  sudo docker compose ps

To inspect the live output logs of your Wi-Fi data pipeline and database:

  sudo docker compose logs -f


--- Troubleshooting Quick Reference ---
* To stop the system: 
  sudo docker compose down

* To restart a specific service (e.g., if code changes are made):
  sudo docker compose restart <container_name>

* To view real-time logs for a single service:
  sudo docker compose logs -f <container_name>

* Port configurations:
  - Grafana Dashboard: http://localhost:3000 (or http://<pi_ip_address>:3000)
  - InfluxDB UI: http://localhost:8086 (or http://<pi_ip_address>:8086)
  - Prometheus Query Builder:  http://localhost:9090 (or http://<pi_ip>:9090)
  - Wi-Fi Exporter Metrics:   http://localhost:8000 (or http://<pi_ip>:8000)
========================================================================
