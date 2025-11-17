#!/bin/sh
echo "Content-Type: application/json"
echo ""

CMD=$(echo "$QUERY_STRING" | cut -d'=' -f2)

if [ "$CMD" = "start" ]; then
    echo 1 > ../status.txt
    echo '{"status":"VPN START"}'

elif [ "$CMD" = "stop" ]; then
    echo 0 > ../status.txt
    killall openvpn
    echo '{"status":"VPN STOP"}'

elif [ "$CMD" = "rotate" ]; then
    echo 2 > ../status.txt
    echo '{"status":"VPN ROTATE"}'

else
    echo '{"status":"UNKNOWN COMMAND"}'
fi
