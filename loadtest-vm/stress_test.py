import argparse
import multiprocessing
import threading
import time
import psutil
import os
import tempfile
import socket

# ========== CPU STRESS ==========
def cpu_stress():
    while True:
        _ = 1 + 1

# ========== MEMORY STRESS ==========
def memory_stress(size_mb):
    data = []
    block = b'x' * 1024 * 1024  # 1 MB
    for _ in range(size_mb):
        data.append(block)
    while True:
        time.sleep(1)

# ========== DISK STRESS ==========
def disk_stress(temp_dir):
    path = os.path.join(temp_dir, "stress_file.tmp")
    with open(path, "wb") as f:
        while True:
            f.write(os.urandom(1024 * 1024))  # 1 MB
            f.flush()
            os.fsync(f.fileno())

# ========== NETWORK STRESS (localhost) ==========
def network_server(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", port))
    s.listen()
    while True:
        conn, _ = s.accept()
        threading.Thread(target=network_handler, args=(conn,), daemon=True).start()

def network_handler(conn):
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            conn.sendall(data)
    finally:
        conn.close()

def network_client(port):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            while True:
                s.sendall(b'x' * 4096)
                s.recv(4096)
        except Exception:
            time.sleep(1)

# ========== MAIN FUNCTION ==========
def main(duration):
    print(f"Starting stress test for {duration} seconds...")

    temp_dir = tempfile.mkdtemp()
    port = 50007
    procs = []

    # CPU - 1 process per core
    for _ in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=cpu_stress)
        p.start()
        procs.append(p)

    # Memory - allocate 100MB
    p = multiprocessing.Process(target=memory_stress, args=(100,))
    p.start()
    procs.append(p)

    # Disk - write continuously
    p = multiprocessing.Process(target=disk_stress, args=(temp_dir,))
    p.start()
    procs.append(p)

    # Network - server + client
    threading.Thread(target=network_server, args=(port,), daemon=True).start()
    p = multiprocessing.Process(target=network_client, args=(port,))
    p.start()
    procs.append(p)

    # Timer
    time.sleep(duration)

    print("Stopping all stress processes...")
    for p in procs:
        p.terminate()
        p.join()

    try:
        os.remove(os.path.join(temp_dir, "stress_file.tmp"))
        os.rmdir(temp_dir)
    except Exception:
        pass

    print("Stress test completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CPU, Memory, Disk, Network stress test")
    parser.add_argument("-t", "--time", type=int, default=30, help="Duration of the test in seconds (default: 30)")
    args = parser.parse_args()
    main(args.time)
