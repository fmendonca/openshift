import argparse
import multiprocessing
import threading
import time
import os
import tempfile
import socket
import psutil
import json
from tqdm import tqdm

# ========== HARDWARE INFO ==========
def get_machine_info():
    return {
        "cpu_cores": psutil.cpu_count(logical=True),
        "memory_total_mb": psutil.virtual_memory().total // (1024 * 1024),
        "disk_free_mb": psutil.disk_usage("/").free // (1024 * 1024),
        "net_interfaces": psutil.net_if_addrs()
    }

# ========== CPU STRESS ==========
def cpu_worker(stop_event):
    while not stop_event.is_set():
        pass

def run_cpu_stress(percent, duration, report):
    total_cores = psutil.cpu_count()
    num_cores = max(1, int((percent / 100) * total_cores))
    stop_event = multiprocessing.Event()
    processes = []

    print(f"\n🧠 Iniciando CPU Stress: {percent}% de {total_cores} núcleos por {duration}s")

    for _ in range(num_cores):
        p = multiprocessing.Process(target=cpu_worker, args=(stop_event,))
        p.start()
        processes.append(p)

    cpu_samples = []
    for _ in tqdm(range(duration), desc="CPU", unit="s"):
        cpu_samples.append(psutil.cpu_percent(interval=1))

    stop_event.set()
    for p in processes:
        p.terminate()
        p.join()

    report["cpu"] = {
        "percent_requested": percent,
        "duration_sec": duration,
        "average_cpu_percent": sum(cpu_samples) / len(cpu_samples)
    }

# ========== MEMORY STRESS ==========
def memory_worker(mb, stop_event):
    block = b'x' * 1024 * 1024
    mem = [block] * mb
    while not stop_event.is_set():
        time.sleep(1)

def run_memory_stress(percent, duration, report):
    total_mem_mb = psutil.virtual_memory().total // (1024 * 1024)
    use_mb = max(1, int((percent / 100) * total_mem_mb))
    stop_event = multiprocessing.Event()
    p = multiprocessing.Process(target=memory_worker, args=(use_mb, stop_event))

    print(f"\n📦 Iniciando Memory Stress: {percent}% de {total_mem_mb}MB (~{use_mb}MB) por {duration}s")

    p.start()
    mem_max = 0
    for _ in tqdm(range(duration), desc="MEM", unit="s"):
        mem = psutil.virtual_memory()
        mem_max = max(mem_max, mem.percent)
        time.sleep(1)

    stop_event.set()
    p.terminate()
    p.join()

    report["memory"] = {
        "percent_requested": percent,
        "duration_sec": duration,
        "max_memory_percent": mem_max
    }

# ========== DISK STRESS ==========
def disk_worker(path, stop_event):
    with open(path, "wb") as f:
        while not stop_event.is_set():
            f.write(os.urandom(1024 * 1024))  # 1MB
            f.flush()
            os.fsync(f.fileno())

def run_disk_stress(percent, duration, report):
    total_disk_mb = psutil.disk_usage("/").free // (1024 * 1024)
    stop_event = multiprocessing.Event()
    path = os.path.join(tempfile.gettempdir(), "stress_disk.tmp")
    p = multiprocessing.Process(target=disk_worker, args=(path, stop_event))

    print(f"\n💾 Iniciando Disk Stress: {percent}% de uso por {duration}s")

    disk_before = psutil.disk_io_counters()
    p.start()

    for _ in tqdm(range(duration), desc="DISK", unit="s"):
        time.sleep(1)

    stop_event.set()
    p.terminate()
    p.join()

    disk_after = psutil.disk_io_counters()
    try:
        os.remove(path)
    except Exception:
        pass

    report["disk"] = {
        "percent_requested": percent,
        "duration_sec": duration,
        "mb_written": (disk_after.write_bytes - disk_before.write_bytes) / (1024 * 1024)
    }

# ========== NETWORK STRESS ==========
def network_server(port, stop_flag):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("127.0.0.1", port))
    server.listen()
    server.settimeout(1)
    while not stop_flag.is_set():
        try:
            conn, _ = server.accept()
            threading.Thread(target=network_echo, args=(conn, stop_flag), daemon=True).start()
        except socket.timeout:
            continue

def network_echo(conn, stop_flag):
    try:
        while not stop_flag.is_set():
            data = conn.recv(4096)
            if not data:
                break
            conn.sendall(data)
    except Exception:
        pass
    finally:
        conn.close()

def network_client(port, stop_flag):
    while not stop_flag.is_set():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            while not stop_flag.is_set():
                s.sendall(b'x' * 4096)
                s.recv(4096)
        except Exception:
            time.sleep(1)

def run_network_stress(percent, duration, report):
    print(f"\n🌐 Iniciando Network Stress: {percent}% de carga local por {duration}s")
    net_before = psutil.net_io_counters()
    stop_flag = threading.Event()
    port = 50007

    server_thread = threading.Thread(target=network_server, args=(port, stop_flag), daemon=True)
    server_thread.start()

    clients = []
    num_clients = max(1, int((percent / 100) * 10))  # até 10 clientes para simular carga

    for _ in range(num_clients):
        t = threading.Thread(target=network_client, args=(port, stop_flag), daemon=True)
        t.start()
        clients.append(t)

    for _ in tqdm(range(duration), desc="NET", unit="s"):
        time.sleep(1)

    stop_flag.set()
    time.sleep(1)  # dá tempo para encerrar

    net_after = psutil.net_io_counters()
    report["network"] = {
        "percent_requested": percent,
        "duration_sec": duration,
        "mb_sent": (net_after.bytes_sent - net_before.bytes_sent) / (1024 * 1024),
        "mb_recv": (net_after.bytes_recv - net_before.bytes_recv) / (1024 * 1024)
    }

# ========== MAIN ==========
def main():
    parser = argparse.ArgumentParser(description="Teste de carga sequencial com barra e relatório JSON")
    parser.add_argument("--cpu", type=int, default=0, help="Porcentagem de uso de CPU")
    parser.add_argument("--cpu-time", type=int, default=0, help="Tempo de uso da CPU (s)")
    parser.add_argument("--memory", type=int, default=0, help="Porcentagem de uso de RAM")
    parser.add_argument("--memory-time", type=int, default=0, help="Tempo de uso da RAM (s)")
    parser.add_argument("--disk", type=int, default=0, help="Porcentagem de uso de disco")
    parser.add_argument("--disk-time", type=int, default=0, help="Tempo de uso do disco (s)")
    parser.add_argument("--network", type=int, default=0, help="Porcentagem de uso da rede")
    parser.add_argument("--network-time", type=int, default=0, help="Tempo de uso da rede (s)")
    parser.add_argument("--output", default="stress_report.json", help="Arquivo de saída JSON")
    args = parser.parse_args()

    machine_info = get_machine_info()
    report = {"machine_info": machine_info}

    if args.cpu and args.cpu_time:
        run_cpu_stress(args.cpu, args.cpu_time, report)

    if args.memory and args.memory_time:
        run_memory_stress(args.memory, args.memory_time, report)

    if args.disk and args.disk_time:
        run_disk_stress(args.disk, args.disk_time, report)

    if args.network and args.network_time:
        run_network_stress(args.network, args.network_time, report)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=4)

    print(f"\n📁 Relatório salvo em {args.output}")

if __name__ == "__main__":
    main()
