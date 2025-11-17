#!/bin/bash
killall openvpn 2>/dev/null
echo "VPN CHANGE"
echo "1" > status.txt
