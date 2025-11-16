#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import struct
import os

SOCKS_PORT = 30999

def handle_client(conn):
    try:
        # ========== HANDSHAKE ==========
        version, nmethods = conn.recv(2)
        conn.recv(nmethods)
        conn.sendall(b"\x05\x00")  # NO AUTH

        # ========== REQUEST HEADER ==========
        ver, cmd, _, atyp = conn.recv(4)

        # CMD harus 1 = CONNECT
        if cmd != 1:
            conn.close()
            return

        # ========== PARSING ADDRESS ==========
        if atyp == 1:  # IPv4
            addr = socket.inet_ntoa(conn.recv(4))
        elif atyp == 3:  # DOMAIN
            domain_len = conn.recv(1)[0]
            addr = conn.recv(domain_len).decode()
        else:
            conn.close()
            return

        port = struct.unpack(">H", conn.recv(2))[0]

        # ========== CONNECT KE SERVER ASLI ==========
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.connect((addr, port))

        # balas success
        reply = b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        conn.sendall(reply)

        # ========== FORWARD 2 ARAH ==========
        threading.Thread(target=pipe, args=(conn, remote)).start()
        threading.Thread(target=pipe, args=(remote, conn)).start()

    except Exception as e:
        print("[ERR]", e)
        try: conn.close()
        except: pass

def pipe(src, dst):
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

def start_server():
    if os.system(f"fuser -k {SOCKS_PORT}/tcp >/dev/null 2>&1") == 0:
        print("Killed previous process.")

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", SOCKS_PORT))
    server.listen(200)

    print(f"[SOCKS5] Running on 0.0.0.0:{SOCKS_PORT}")

    while True:
        conn, addr = server.accept()
        print("[Client]", addr)
        threading.Thread(target=handle_client, args=(conn,)).start()

if __name__ == "__main__":
    start_server()
