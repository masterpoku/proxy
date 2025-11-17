#!/usr/bin/env python3
import os
import socket, threading, time

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

        port = int.from_bytes(client.recv(2), 'big')
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


def start_socks():
    while True:
        try:
            server = socket.socket()
            server.bind(("0.0.0.0", LOCAL_PORT))
            server.listen(200)
            print(f"[SOCKS5] Running on {LOCAL_PORT}")
            break
        except:
            print("[SOCKS5] Port busy, retry 2s")
            time.sleep(2)

    while True:
        c, _ = server.accept()
        threading.Thread(target=handle_client, args=(c,), daemon=True).start()


if __name__ == "__main__":
    start_socks()
