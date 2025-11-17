#!/bin/bash

OVPN_DIR="OpenVPN256"
STATUS_FILE="status.txt"
CURRENT_OVPN=""

while true
do
    STATUS=$(cat $STATUS_FILE)

    # 0 = stop VPN
    if [ "$STATUS" = "0" ]; then
        killall openvpn 2>/dev/null
        sleep 1
        CURRENT_OVPN=""
        echo "[VPN] OFF"
    fi

    # 2 = rotate
    if [ "$STATUS" = "2" ]; then
        echo "[VPN] ROTATE REQUEST"

        killall openvpn 2>/dev/null
        sleep 1

        FILES=("$OVPN_DIR"/*.ovpn)
        RANDOM_OVPN=${FILES[$RANDOM % ${#FILES[@]}]}
        CURRENT_OVPN="$RANDOM_OVPN"

        echo "[VPN] Start with: $CURRENT_OVPN"
        sudo openvpn --config "$CURRENT_OVPN" --auth-user-pass auth.txt --daemon

        echo "1" > $STATUS_FILE  # balik ke status ON
    fi

    # 1 = start (only if not running)
    if [ "$STATUS" = "1" ]; then
        if ! pgrep -x "openvpn" >/dev/null; then
            echo "[VPN] Starting..."

            FILES=("$OVPN_DIR"/*.ovpn)
            RANDOM_OVPN=${FILES[$RANDOM % ${#FILES[@]}]}
            CURRENT_OVPN="$RANDOM_OVPN"

            echo "[VPN] Using: $CURRENT_OVPN"
            sudo openvpn --config "$CURRENT_OVPN" --auth-user-pass auth.txt --daemon
        fi
    fi

    sleep 2
done
