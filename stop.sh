#!/bin/bash
killall openvpn 2>/dev/null
echo "VPN STOPPED"
echo "3" > status.txt
