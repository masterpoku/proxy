#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import threading
import os
import time

# ====================================
# KONFIGURASI SOCKS5 LOKAL
# ====================================
LOCAL_HOST = "0.0.0.0"
LOCAL_PORT = 30999

# ====================================
# Utility forwarding
# ====================================

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
        try:
            src.close()
        except:
            pass
        try:
            dst.close()
        except:
            pass

# ====================================
# Handler SOCKS5
# ====================================

def handle_client(client_sock, client_addr):
    try:
        # === 1) Handshake ===
        # Client: VER, NMETHODS
        header = client_sock.recv(2)
        if len(header) < 2:
            client_sock.close()
            return

        ver, nmethods = header[0], header[1]
        if ver != 5:
            client_sock.close()
            return

        # Baca daftar methods
        methods = client_sock.recv(nmethods)
        # Jawab: version 5, no auth (0x00)
        client_sock.sendall(b"\x05\x00")

        # === 2) Request ===
        # VER CMD RSV ATYP
        req = client_sock.recv(4)
        if len(req) < 4:
            client_sock.close()
            return

        ver, cmd, rsv, atyp = req

        if ver != 5 or cmd != 1:  # CMD 1 = CONNECT
            # reply: command not supported
            client_sock.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            client_sock.close()
            return

        # === 3) Parse address ===
        if atyp == 1:  # IPv4
            addr_bytes = client_sock.recv(4)
            dst_addr = socket.inet_ntoa(addr_bytes)
        elif atyp == 3:  # DOMAIN
            domain_len = client_sock.recv(1)[0]
            domain_bytes = client_sock.recv(domain_len)
            dst_addr = domain_bytes.decode()
        elif atyp == 4:  # IPv6 (optional)
            addr_bytes = client_sock.recv(16)
            dst_addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            client_sock.close()
            return

        # Port (2 bytes, big-endian)
        port_bytes = client_sock.recv(2)
        dst_port = int.from_bytes(port_bytes, "big")

        # === 4) Connect ke tujuan langsung ===
        try:
            remote = socket.create_connection((dst_addr, dst_port), timeout=10)
        except Exception:
            # connection refused / timeout
            client_sock.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            client_sock.close()
            return

        # === 5) Reply sukses ke client ===
        # VER=5, REP=0 (sukses), RSV=0, ATYP=1, BND.ADDR=0.0.0.0, BND.PORT=0
        resp = b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        client_sock.sendall(resp)

        # === 6) Mulai forward data dua arah ===
        t1 = threading.Thread(target=forward, args=(client_sock, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client_sock), daemon=True)
        t1.start()
        t2.start()

    except Exception:
        try:
            client_sock.close()
        except:
            pass


# ====================================
# MAIN SERVER
# ====================================

def main():
    # Pastikan port bebas
    os.system(f"fuser -k {LOCAL_PORT}/tcp >/dev/null 2>&1")

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((LOCAL_HOST, LOCAL_PORT))
    srv.listen(256)

    print(f"🌐 SOCKS5 lokal berjalan di {LOCAL_HOST}:{LOCAL_PORT}")
    print("   Tidak pakai upstream, routing lewat OS (OpenVPN/tun0)")

    while True:
        try:
            client, addr = srv.accept()
            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()
        except KeyboardInterrupt:
            print("\n[SOCKS5] Stop by KeyboardInterrupt")
            break
        except Exception:
            time.sleep(0.1)
            continue

    try:
        srv.close()
    except:
        pass


if __name__ == "__main__":
    main()
