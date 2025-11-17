#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import socket
import threading
import time
from flask import Flask, jsonify

# ======================================================
#                 SOCKS5 SERVER
# ======================================================

LOCAL_PORT = 30999
os.system(f"fuser -k {LOCAL_PORT}/tcp >/dev/null 2>&1")

def handle_client(client):
    try:
        client.recv(262)
        client.sendall(b"\x05\x00")

        data = client.recv(4)
        atyp = data[3]

        if atyp == 1:
            addr = socket.inet_ntoa(client.recv(4))
        elif atyp == 3:
            length = client.recv(1)[0]
            addr = client.recv(length).decode()
        else:
            client.close()
            return

        port = int.from_bytes(client.recv(2), "big")
        remote = socket.create_connection((addr, port))

        reply = b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        client.sendall(reply)

    except:
        client.close()
        return

    def relay(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data:
                    break
                dst.sendall(data)
        except:
            pass
        finally:
            src.close()
            dst.close()

    threading.Thread(target=relay, args=(client, remote), daemon=True).start()
    threading.Thread(target=relay, args=(remote, client), daemon=True).start()


def start_socks_thread():
    def run_socks():
        while True:
            try:
                server = socket.socket()
                server.bind(("0.0.0.0", LOCAL_PORT))
                server.listen(200)
                print(f"[SOCKS5] Running on {LOCAL_PORT}")
                break
            except:
                print("[SOCKS5] Port busy, retrying 2s…")
                time.sleep(2)

        while True:
            client, _ = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()

    threading.Thread(target=run_socks, daemon=True).start()


# ======================================================
#                 FLASK CONTROL API
# ======================================================

app = Flask(__name__)
STATUS_FILE = "status.txt"

def write_status(val):
    with open(STATUS_FILE, "w") as f:
        f.write(str(val))

def read_status():
    return open(STATUS_FILE).read().strip()

@app.get("/start")
def start():
    write_status(1)
    return jsonify({"status": "START REQUEST SENT"})

@app.get("/stop")
def stop():
    write_status(0)
    return jsonify({"status": "STOP REQUEST SENT"})

@app.get("/rotate")
def rotate():
    write_status(2)
    return jsonify({"status": "ROTATE REQUEST SENT"})

@app.get("/status")
def status():
    running = os.system("pgrep openvpn >/dev/null") == 0
    ip = os.popen("curl -s https://api.ipify.org").read().strip()
    return jsonify({
        "vpn_running": running,
        "vpn_status": read_status(),
        "ip": ip
    })


# ======================================================
#                 MAIN ENTRY
# ======================================================

if __name__ == "__main__":
    print("🔥 Starting SOCKS5 server…")
    start_socks_thread()

    print("🔥 Starting Flask API on port 5000…")
    app.run(host="0.0.0.0", port=5000, debug=False)
