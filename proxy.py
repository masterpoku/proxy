#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import time
import os
from flask import Flask, jsonify

# ==============================================
# KONFIGURASI PROXY LOKAL
# ==============================================
LOCAL_SOCKS_PORT = 30999

# bersihkan port jika kepake
os.system(f"fuser -k {LOCAL_SOCKS_PORT}/tcp >/dev/null 2>&1")

# ==============================================
# FLASK API
# ==============================================
app = Flask(__name__)

@app.get("/status")
def status():
    return jsonify({"running": True})

@app.get("/exit")
def exit_app():
    print("❌ EXIT requested via /exit")
    os._exit(0)

def run_flask():
    print("🌐 Flask running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

# ==============================================
# FORWARDING
# ==============================================
def forward(src, dst):
    try:
        while True:
            data = src.recv(4096)
            if not data:
                break
            dst.sendall(data)
    except:
        pass
    finally:
        try: src.close()
        except: pass
        try: dst.close()
        except: pass

# ==============================================
# HANDLE CLIENT (SOCKS5)
# ==============================================
def handle_client(client_sock):
    try:
        # handshake
        data = client_sock.recv(2)
        if len(data) < 2 or data[0] != 5:
            client_sock.close()
            return

        n_methods = data[1]
        client_sock.recv(n_methods)
        client_sock.sendall(b"\x05\x00")  # no auth

        # request
        data = client_sock.recv(4)
        if len(data) < 4 or data[1] != 1:
            client_sock.close()
            return

        atyp = data[3]

        if atyp == 1:  # IPv4
            addr = socket.inet_ntoa(client_sock.recv(4))
        elif atyp == 3:  # domain
            ln = client_sock.recv(1)[0]
            addr = client_sock.recv(ln).decode()
        else:
            client_sock.close()
            return

        port = int.from_bytes(client_sock.recv(2), "big")

        print(f"[SOCKS] Client requests {addr}:{port}")

        # CONNECT langsung ke internet (no upstream)
        dst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        dst.connect((addr, port))

        # reply success
        reply = b"\x05\x00\x00\x01" + socket.inet_aton("0.0.0.0") + b"\x00\x00"
        client_sock.sendall(reply)

        # forward dua arah
        threading.Thread(target=forward, args=(client_sock, dst), daemon=True).start()
        threading.Thread(target=forward, args=(dst, client_sock), daemon=True).start()

    except Exception as e:
        print("[ERROR]", e)
        try: client_sock.close()
        except: pass

# ==============================================
# SOCKS5 SERVER
# ==============================================
def run_socks():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # agar bisa dipakai laptop B
    s.bind(("0.0.0.0", LOCAL_SOCKS_PORT))

    s.listen(200)
    print(f"[SOCKS5] Listening on 0.0.0.0:{LOCAL_SOCKS_PORT}")

    while True:
        c, addr = s.accept()
        print(f"[NEW CLIENT] {addr}")
        threading.Thread(target=handle_client, args=(c,), daemon=True).start()

# ==============================================
# MAIN
# ==============================================
if __name__ == "__main__":
    # start SOCKS5
    threading.Thread(target=run_socks, daemon=True).start()

    # start Flask
    threading.Thread(target=run_flask, daemon=True).start()

    print("🔥 PROXY SERVER ACTIVE (NO UPSTREAM)")
    print(f"   SOCKS5  : 0.0.0.0:{LOCAL_SOCKS_PORT}")
    print("   FLASK   : http://0.0.0.0:5000")

    while True:
        time.sleep(1)
