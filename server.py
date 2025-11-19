from flask import Flask, jsonify
import os, time

CMD_FILE = "vpn_cmd.txt"
IP_FILE  = "ip.txt"

app = Flask(__name__)

@app.get("/start")
def start_vpn():
    open(CMD_FILE, "w").write("START")
    time.sleep(1)
    return jsonify({"status": "START_TRIGGER_SENT"})

@app.get("/stop")
def stop_vpn():
    open(CMD_FILE, "w").write("STOP")
    os.system("bash stop")
    time.sleep(1)
    return jsonify({"status": "STOP_TRIGGER_SENT"})

@app.get("/status")
def status():
    running = os.system("pgrep openvpn >/dev/null") == 0

    ip = "UNKNOWN"
    if os.path.isfile(IP_FILE):
        ip = open(IP_FILE).read().strip()

    return jsonify({"running": running, "ip": ip})

app.run(host="0.0.0.0", port=5000, debug=False)
