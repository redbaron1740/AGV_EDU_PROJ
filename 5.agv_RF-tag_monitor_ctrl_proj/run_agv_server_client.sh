#!/bin/bash
python3 agv_station_server.py &
sleep 2
python3 agv_control_client.py