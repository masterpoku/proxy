#!/bin/bash

OVPN_DIR="OpenVPN256"

while true
do
    echo "========================================="
    echo " 🔄 ROTATE VPN $(date '+%Y-%m-%d %H:%M:%S')"
    echo "========================================="

    # Hentikan VPN lama
    killall openvpn 2>/dev/null
    sleep 1

    # Ambil list file .ovpn
    FILES=("$OVPN_DIR"/*.ovpn)

    # Pilih random file
    RANDOM_OVPN=${FILES[$RANDOM % ${#FILES[@]}]}

    echo "🌍 Menggunakan config: $RANDOM_OVPN"

    # Start VPN (foreground supaya loop tunggu sampai selesai)
    sudo openvpn --config "$RANDOM_OVPN" --auth-user-pass auth.txt

    echo "⚠️  VPN DISCONNECTED! Mengganti server..."
    sleep 2
done
