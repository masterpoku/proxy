#!/bin/bash

OVPN_DIR="OpenVPN256"
STATUS_FILE="status.txt"
CURRENT_OVPN=""

while true
do
    STATUS=$(cat "$STATUS_FILE")

    # ===== STOP =====
    if [ "$STATUS" = "0" ]; then
        killall openvpn 2>/dev/null
        sleep 1
        CURRENT_OVPN=""
        echo "[VPN] OFF"
    fi

    # ===== ROTATE =====
    if [ "$STATUS" = "2" ]; then
        echo "[VPN] ROTATE REQUEST"
        killall openvpn 2>/dev/null
        sleep 1

        FILES=("$OVPN_DIR"/*.ovpn)
        RANDOM_OVPN="${FILES[$RANDOM % ${#FILES[@]}]}"
        CURRENT_OVPN="$RANDOM_OVPN"

        echo "[VPN] Using: $CURRENT_OVPN"
        sudo openvpn --config "$CURRENT_OVPN" --auth-user-pass auth.txt --daemon
        sleep 3

        echo "3" > "$STATUS_FILE"   # → STANDBY
        continue
    fi

    # ===== START =====
    if [ "$STATUS" = "1" ]; then

        # cek apakah openvpn sudah hidup
        if ! pgrep -f "openvpn --config" >/dev/null; then
            echo "[VPN] Starting..."

            FILES=("$OVPN_DIR"/*.ovpn)
            RANDOM_OVPN="${FILES[$RANDOM % ${#FILES[@]}]}"
            CURRENT_OVPN="$RANDOM_OVPN"

            echo "[VPN] Using: $CURRENT_OVPN"
            sudo openvpn --config "$CURRENT_OVPN" 
            sleep 3

            echo "3" > "$STATUS_FILE"   # → STANDBY
        else
            echo "[VPN] Already running → Switch to STANDBY"
            echo "3" > "$STATUS_FILE"
        fi
    fi

    sleep 1
done
