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
        pass  # Ocupa CPU continuamente

# ========== MEMORY STRESS ==========
def memory_stress(size_mb):
    block = b'x' * 1024 * 1024  # 1MB
    memory = [block] * size_mb
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

# ========== DISK STRESS ==========
def disk_stress(path):
    try:
        with open(path, "wb") as f:
            while True:
                f.write(os.urandom(1024 * 1024))  # 1MB
                f.flush()
                os.fsync(f.fileno())
    except KeyboardInterrupt:
        pass

# ========== NETWORK SERVER ==========
def network_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))
    server.listen(1)
    while True:
        conn, _ = server.accept()
        threading.Thread(target=network_echo, args=(conn,), daemon=True).start()

def network_echo(conn):
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            conn.sendall(data)
    finally:
        conn.close()

# ========== NETWORK CLIENT ==========
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

# ========== MAIN ==========
def main(duration):
    print(f"⏱️ Iniciando teste de carga por {duration} segundos...")

    processes = []
    temp_dir = tempfile.gettempdir()
    disk_path = os.path.join(temp_dir, "stress_disk.tmp")
    net_port = 50007

    # CPU
    for _ in range(multiprocessing.cpu_count()):
        p = multiprocessing.Process(target=cpu_stress)
        p.start()
        processes.append(p)

    # Memory (~100 MB)
    mem_proc = multiprocessing.Process(target=memory_stress, args=(100,))
    mem_proc.start()
    processes.append(mem_proc)

    # Disk
    disk_proc = multiprocessing.Process(target=disk_stress, args=(disk_path,))
    disk_proc.start()
    processes.append(disk_proc)

    # Network server
    server_thread = threading.Thread(target=network_server, args=(net_port,), daemon=True)
    server_thread.start()

    # Network client
    net_proc = multiprocessing.Process(target=network_client, args=(net_port,))
    net_proc.start()
    processes.append(net_proc)

    # Espera o tempo solicitado
    time.sleep(duration)

    print("✅ Finalizando processos...")
    for p in processes:
        p.terminate()
        p.join()

    try:
        os.remove(disk_path)
    except Exception:
        pass

    print("🏁 Teste de carga finalizado.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--time", type=int, default=30, help="Duração em segundos (padrão: 30)")
    args = parser.parse_args()
    main(args.time)
