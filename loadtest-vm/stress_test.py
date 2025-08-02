import argparse
import multiprocessing
import threading
import time
import os
import tempfile
import socket
import psutil

# ========== STRESS FUNCTIONS ==========
def cpu_stress():
    while True:
        pass

def memory_stress(size_mb):
    block = b'x' * 1024 * 1024
    memory = [block] * size_mb
    while True:
        time.sleep(1)

def disk_stress(path):
    with open(path, "wb") as f:
        while True:
            f.write(os.urandom(1024 * 1024))
            f.flush()
            os.fsync(f.fileno())

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

    # Coleta inicial de métricas
    cpu_samples = []
    mem_max = 0
    disk_before = psutil.disk_io_counters()
    net_before = psutil.net_io_counters()

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

    # Monitoramento paralelo
    for _ in range(args.time):
        cpu_samples.append(psutil.cpu_percent(interval=1))
        mem = psutil.virtual_memory()
        mem_max = max(mem_max, mem.percent)

    print("✅ Finalizando processos...")
    for p in processes:
        p.terminate()
        p.join()

    # Remove arquivos de disco
    for i in range(args.disk):
        try:
            os.remove(os.path.join(temp_dir, f"stress_disk_{i}.tmp"))
        except Exception:
            pass

    # Métricas finais
    disk_after = psutil.disk_io_counters()
    net_after = psutil.net_io_counters()

    print("\n📊 RELATÓRIO FINAL")
    print(f"- CPU média: {sum(cpu_samples) / len(cpu_samples):.2f}%")
    print(f"- Memória pico: {mem_max:.2f}%")
    print(f"- Escrita em disco: {(disk_after.write_bytes - disk_before.write_bytes) / (1024 ** 2):.2f} MB")
    print(f"- Leitura em disco: {(disk_after.read_bytes - disk_before.read_bytes) / (1024 ** 2):.2f} MB")
    print(f"- Rede enviada: {(net_after.bytes_sent - net_before.bytes_sent) / (1024 ** 2):.2f} MB")
    print(f"- Rede recebida: {(net_after.bytes_recv - net_before.bytes_recv) / (1024 ** 2):.2f} MB")
    print("🏁 Teste finalizado com sucesso.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de carga parametrizável com relatório")
    parser.add_argument("-t", "--time", type=int, default=30, help="Duração do teste (segundos)")
    parser.add_argument("--cpu", type=int, default=0, help="Número de processos de carga de CPU")
    parser.add_argument("--memory", type=int, default=0, help="Memória a alocar em MB")
    parser.add_argument("--disk", type=int, default=0, help="Número de processos de escrita em disco")
    parser.add_argument("--network", type=int, default=0, help="Número de clientes TCP")
    args = parser.parse_args()
    main(args)
