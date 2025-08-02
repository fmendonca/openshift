import argparse
import multiprocessing
import threading
import time
import os
import tempfile
import socket

# ========== CPU STRESS ==========
def cpu_stress():
    while True:
        pass

# ========== MEMORY STRESS ==========
def memory_stress(size_mb):
    block = b'x' * 1024 * 1024  # 1MB
    memory = [block] * size_mb
    while True:
        time.sleep(1)

# ========== DISK STRESS ==========
def disk_stress(path):
    with open(path, "wb") as f:
        while True:
            f.write(os.urandom(1024 * 1024))  # 1MB
            f.flush()
            os.fsync(f.fileno())

# ========== NETWORK SERVER ==========
def network_server(port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))
    server.listen()
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
def main(args):
    print(f"⏱️ Executando stress test por {args.time} segundos...")

    processes = []
    temp_dir = tempfile.gettempdir()
    net_port = 50007

    # CPU
    if args.cpu:
        for _ in range(args.cpu):
            p = multiprocessing.Process(target=cpu_stress)
            p.start()
            processes.append(p)

    # Memória
    if args.memory:
        p = multiprocessing.Process(target=memory_stress, args=(args.memory,))
        p.start()
        processes.append(p)

    # Disco
    if args.disk:
        for i in range(args.disk):
            path = os.path.join(temp_dir, f"stress_disk_{i}.tmp")
            p = multiprocessing.Process(target=disk_stress, args=(path,))
            p.start()
            processes.append(p)

    # Rede
    if args.network:
        server_thread = threading.Thread(target=network_server, args=(net_port,), daemon=True)
        server_thread.start()

        for _ in range(args.network):
            p = multiprocessing.Process(target=network_client, args=(net_port,))
            p.start()
            processes.append(p)

    # Aguarda o tempo solicitado
    time.sleep(args.time)

    print("✅ Finalizando processos...")
    for p in processes:
        p.terminate()
        p.join()

    # Remove arquivos temporários de disco
    for i in range(args.disk):
        try:
            os.remove(os.path.join(temp_dir, f"stress_disk_{i}.tmp"))
        except Exception:
            pass

    print("🏁 Teste finalizado com sucesso.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de carga parametrizável")
    parser.add_argument("-t", "--time", type=int, default=30, help="Duração do teste (segundos)")
    parser.add_argument("--cpu", type=int, default=0, help="Número de processos de carga de CPU")
    parser.add_argument("--memory", type=int, default=0, help="Memória a alocar em MB")
    parser.add_argument("--disk", type=int, default=0, help="Número de processos de escrita em disco")
    parser.add_argument("--network", type=int, default=0, help="Número de clientes de rede TCP")
    args = parser.parse_args()
    main(args)
