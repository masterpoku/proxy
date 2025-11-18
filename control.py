#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import subprocess
import requests
from flask import Flask, jsonify

# ======================================
# KONFIGURASI
# ======================================

# Folder semua .ovpn (boleh relative seperti di log kamu)
OVPN_DIR = "OpenVPN256"

# File user/pass kalau .ovpn pakai auth-user-pass
AUTH_FILE = "auth.txt"          # kalau ga pakai auth-user-pass, biarin aja

# Lokasi log openvpn
LOG_FILE = "/var/log/openvpn.log"

# Socks5 lokal (proxy_forwarder.py)
SOCKS_PORT = 30999

# Maksimal waktu nunggu VPN bener-bener ready (detik)
TIMEOUT_CONNECT = 40

# Global state
CURRENT_OVPN = None

app = Flask(__name__)


# ======================================
# UTIL UMUM
# ======================================

def sh(cmd: str) -> int:
    """Jalankan shell command, return exit code."""
    return os.system(cmd)


def stop_socks5():
    """Matikan socks5 forwarder (proxy_forwarder.py) & bebasin port."""
    sh("pkill -f proxy_forwarder.py 2>/dev/null")
    sh(f"fuser -k {SOCKS_PORT}/tcp 2>/dev/null")
    print("[SOCKS5] STOPPED")


def start_socks5():
    """Start socks5 forwarder SETELAH VPN ready."""
    stop_socks5()
    # Sesuaikan nama file kalau beda
    subprocess.Popen("python proxy_forwarder.py", shell=True)
    print(f"[SOCKS5] STARTED at 127.0.0.1:{SOCKS_PORT}")


def stop_vpn():
    """Matikan semua proses OpenVPN."""
    global CURRENT_OVPN
    sh("killall openvpn 2>/dev/null")
    CURRENT_OVPN = None
    print("[VPN] STOPPED")
    time.sleep(1)


def wait_for_log_ready() -> bool:
    """
    Tunggu sampai log OpenVPN mengandung 'Initialization Sequence Completed'
    Artinya handshake + tunnel sudah selesai dibuat.
    """
    start = time.time()
    while time.time() - start < TIMEOUT_CONNECT:
        try:
            if os.path.isfile(LOG_FILE):
                with open(LOG_FILE, "r", errors="ignore") as f:
                    if "Initialization Sequence Completed" in f.read():
                        print("[VPN] LOG OK: Initialization Sequence Completed")
                        return True
        except Exception as e:
            print(f"[VPN] LOG READ ERROR: {e}")
        time.sleep(1)
    print("[VPN] LOG TIMEOUT")
    return False


def wait_for_tun0() -> bool:
    """Tunggu sampai interface tun0 muncul."""
    start = time.time()
    while time.time() - start < TIMEOUT_CONNECT:
        if sh("ip a show tun0 >/dev/null 2>&1") == 0:
            print("[VPN] tun0 FOUND")
            return True
        time.sleep(1)
    print("[VPN] tun0 NOT FOUND (TIMEOUT)")
    return False


def get_public_ip() -> str | None:
    """Ambil IP publik sekarang (tanpa peduli sebelumnya)."""
    try:
        r = requests.get("https://api64.ipify.org?format=json", timeout=5)
        r.raise_for_status()
        ip = r.json().get("ip")
        if ip:
            print(f"[VPN] PUBLIC IP: {ip}")
            return ip
    except Exception as e:
        print(f"[VPN] GET IP ERROR: {e}")
    return None


def wait_for_public_ip() -> str | None:
    """Retry beberapa kali sampai bisa dapat IP publik."""
    for _ in range(12):   # 12 x 2 detik ≈ 24 detik
        ip = get_public_ip()
        if ip:
            return ip
        time.sleep(2)
    print("[VPN] FAILED GET PUBLIC IP (TIMEOUT)")
    return None


def start_vpn_random():
    """
    Start OpenVPN pakai file .ovpn random,
    lalu tunggu sampai:
      - log ready
      - tun0 aktif
      - IP publik bisa diambil
    Baru nyalain socks5.
    """
    global CURRENT_OVPN

    # Ambil list .ovpn
    files = []
    if os.path.isdir(OVPN_DIR):
        for name in os.listdir(OVPN_DIR):
            if name.endswith(".ovpn"):
                files.append(os.path.join(OVPN_DIR, name))

    if not files:
        print("[VPN] NO .ovpn FILES FOUND")
        return False, "NO_OVPN_FILES"

    chosen = random.choice(files)
    CURRENT_OVPN = chosen
    print(f"[VPN] CHOSEN OVPN: {chosen}")

    # Bersihin log
    sh(f"> {LOG_FILE}")

    # Start OpenVPN (daemon)
    if os.path.isfile(AUTH_FILE):
        cmd = (
            f"openvpn --daemon "
            f"--config '{chosen}' "
            f"--log '{LOG_FILE}'"
        )
    else:
        cmd = (
            f"openvpn --daemon "
            f"--config '{chosen}' "
            f"--log '{LOG_FILE}'"
        )

    print(f"[VPN] START CMD: {cmd}")
    sh(cmd)

    # 1) Tunggu log 'Initialization Sequence Completed'
    if not wait_for_log_ready():
        stop_vpn()
        return False, "LOG_TIMEOUT"

    # 2) Tunggu interface tun0 aktif
    if not wait_for_tun0():
        stop_vpn()
        return False, "TUN0_NOT_FOUND"

    # (route check dihapus karena environment kamu bisa pakai split route)

    # 3) Tunggu IP publik bisa diambil (harusnya sudah lewat VPN)
    ip = wait_for_public_ip()
    if not ip:
        stop_vpn()
        return False, "PUBLIC_IP_TIMEOUT"

    # 4) Kalau semua OK → start socks5
    start_socks5()

    return True, {"ovpn": chosen, "ip": ip}


# ======================================
# API ENDPOINTS
# ======================================

@app.get("/stop")
def api_stop():
    stop_socks5()
    stop_vpn()
    return jsonify({"status": "STOPPED"})


@app.get("/start")
def api_start():
    stop_socks5()
    ok, detail = start_vpn_random()
    if ok:
        return jsonify({"status": "CONNECTED", "detail": detail})
    return jsonify({"status": "FAILED", "reason": detail})


@app.get("/rotate")
def api_rotate():
    stop_socks5()
    stop_vpn()
    ok, detail = start_vpn_random()
    if ok:
        return jsonify({"status": "ROTATED", "detail": detail})
    return jsonify({"status": "FAILED", "reason": detail})


@app.get("/status")
def api_status():
    running = (sh("pgrep -x openvpn >/dev/null 2>&1") == 0)
    return jsonify({
        "running": running,
        "ovpn": CURRENT_OVPN,
        "ip": get_public_ip(),
        "socks5": f"127.0.0.1:{SOCKS_PORT}"
    })


@app.get("/exit")
def api_exit():
    os._exit(0)


# ======================================
# MAIN
# ======================================

if __name__ == "__main__":
    os.system("fuser -k 5000/tcp > /dev/null 2>&1")
    print("🔥 VPN + SOCKS5 Controller running on 0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
