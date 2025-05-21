import math
import signal
import socket, json, threading, time, subprocess, os
from datetime import datetime
import random
import argparse

HOST = '127.0.0.1'
PORT = 9000
NIVEIS = ['vermelho', 'amarelo', 'verde']


def start_server(salas):
    cmd = ['python', 'manage.py', 'runurgencias',
           f'--host={HOST}', f'--port={PORT}',
           f'--salas={salas}', f'--medicos=1']
    return subprocess.Popen(cmd, preexec_fn=os.setsid)


def patient(pid, level, room):
    ts = datetime.utcnow().isoformat() + 'Z'
    payload = {
        'pid': pid,
        'room': room,
        'urgencia': level,
        'timestamp': ts
    }
    try:
        with socket.create_connection((HOST, PORT), timeout=2) as s:
            s.sendall(json.dumps(payload).encode())
            resp = s.recv(1024)
            print(f"Paciente {pid} ({level}) Hospital recebeu: {resp!r}")
    except Exception as e:
        print(f"[ROOM {room}] Paciente {pid} ERRO: {e}")


def run_burst(start_pid, count, salas, start_room):
    threads = []
    room = start_room
    for i in range(count):
        pid = start_pid + i
        level = random.choice(NIVEIS)
        t = threading.Thread(target=patient, args=(pid, level, room))
        t.start()
        threads.append(t)
        # round‐robin cycle das salas
        room = (room + 1) % salas
        time.sleep(0.05)
    for t in threads:
        t.join()
    # Devolve a sala que ficamos
    return room


if __name__ == '__main__':
    p = argparse.ArgumentParser(
        description="Simular múltiplas salas de urgência"
    )
    p.add_argument('--salas', type=int, default=3, help="Nº de salas e médicos")
    p.add_argument('--pacientes', type=int, default=20, help="Total pacientes")
    p.add_argument('--surto', type=int, default=5, help="Tamanho do surto")
    args = p.parse_args()

    SALAS = args.salas
    PACIENTES = args.pacientes
    SURTO = args.surto

    # limpa os logs
    if os.path.exists('logs.json'):
        os.remove('logs.json')

    # Grava o estado inicial de médicos e salas
    initial = {
        'medicos_totais': SALAS,
        'salas_totais': SALAS,
    }
    with open('logs.json', 'w', encoding='utf-8') as f:
        json.dump(initial, f, ensure_ascii=False, indent=2)

    srv = start_server(SALAS)
    time.sleep(1)

    try:
        # Simula surtos
        pid = 0
        sala = 0
        n_bursts = math.ceil(PACIENTES / SURTO)
        for idx in range(n_bursts):
            resto = PACIENTES - pid
            cnt = SURTO if resto >= SURTO else resto

            # dispara o surto
            sala = run_burst(pid, cnt, SALAS, sala)

            # marca o “surto” nos registros
            try:
                with open('logs.json', 'r+', encoding='utf-8') as f:
                    data = json.load(f)
                    for p_i in range(pid, pid + cnt):
                        key = str(p_i)
                        if key in data:
                            data[key]["surto"] = idx + 1
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.truncate()
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            pid += cnt
            time.sleep(2)

        # Espera até que TODOS os pacientes sejam atendidos ou desistam
        while True:
            try:
                with open('logs.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                done = sum(
                    1 for i in range(PACIENTES)
                    if data.get(str(i), {}).get('saida') is not None
                        or data.get(str(i), {}).get('desistencia') is True
                )
                if done >= PACIENTES:
                    break
            except Exception:
                pass
            time.sleep(1)

        # Regista total de surtos
        try:
            with open('logs.json', 'r+', encoding='utf-8') as f:
                data = json.load(f)
                data['total_surtos'] = n_bursts
                f.seek(0)
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.truncate()
        except Exception:
            pass
    finally:
        # Desliga o servidor só se nós o arrancámos
        print("🏁 Finalizando servidor")
        os.killpg(srv.pid, signal.SIGTERM)
        srv.wait()
        print("✅ Teste concluído. Verifique logs.json e a saída de urgências.")
