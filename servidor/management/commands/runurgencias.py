import socket
import threading
import time
from django.core.management.base import BaseCommand
import heapq
import json
from datetime import datetime

from servidor.rooms import Room
from servidor.constants import (
    URGENCIA_PRIORIDADES,
    TEMPOS_ATENDIMENTO,
    TIMEOUTS,
    MAX_PACIENTES
)

"""
Iniciar servidor TCP de urgências 

Criação do socket TCP, faz bind numa interface e porta configuráveis, 
escuta conexões de pacientes (processos clientes) e envia a confirmação de chegada
"""


class Command(BaseCommand):
    help = "Servidor de urgencias com multi-salas"

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=9000)
        parser.add_argument('--salas', type=int, default=3,
                            help='Número de salas independentes')
        parser.add_argument('--medicos', type=int, default=5,
                            help='Número de médicos por sala')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_lock = threading.Lock()
        # Salas de fila de espera
        self.salas = []
        self._queue_cv = threading.Condition()

    def log_event(self, record):
        try:
            with open('logs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data[str(record['pid'])] = record
        with open('logs.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def handle(self, *args, **opts):
        host = opts['host']
        port = opts['port']
        n_salas = opts['salas']
        n_medicos = opts['medicos']

        # inicializa as filas
        self.salas = [[] for _ in range(n_salas)]
        self._next_sala = 0

        # Thread desistências em todas as salas
        def purge_thread():
            while True:
                time.sleep(1)
                now = datetime.utcnow().isoformat() + 'Z'
                with self._queue_cv:
                    for fila in self.salas:
                        restante = []
                        for priority, ts, pid, payload in fila:
                            nivel = payload.get('urgencia') or payload.get('urgência')
                            waited = (datetime.fromisoformat(now[:-1])
                                      - datetime.fromisoformat(ts[:-1])).total_seconds()
                            if waited > TIMEOUTS.get(nivel, 0):
                                rec = {
                                    "pid": pid,
                                    "medico": None,
                                    "room": None,
                                    "chegada": ts,
                                    "nivel": nivel,
                                    "inicio": None,
                                    "saida": now,
                                    "espera": waited,
                                    "duracao": None,
                                    "desistencia": True
                                }
                                with self._log_lock:
                                    self.log_event(rec)
                            else:
                                restante.append((priority, ts, pid, payload))
                        fila[:] = restante
                        heapq.heapify(fila)

        threading.Thread(target=purge_thread, daemon=True).start()

        # Cada médico fica “fixo” numa sala, mas pode emprestar casos críticos
        def medico_thread(med_id, sala_id):
            while True:
                with self._queue_cv:
                    # Espera que haja pelo menos 1 paciente em x sala
                    while not any(self.salas):
                        self._queue_cv.wait()
                    # Primeiro tenta na sua sala
                    if self.salas[sala_id]:
                        priority, ts, pid, payload = heapq.heappop(self.salas[sala_id])
                    else:
                        # Empresta casos críticos (prioridade 0) de outras salas
                        emprestado = None
                        for i, fila in enumerate(self.salas):
                            if fila and fila[0][0] == 0:
                                emprestado = (i, heapq.heappop(fila))
                                break
                        if emprestado:
                            _, (priority, ts, pid, payload) = emprestado
                        else:
                            # Rouba o de maior urgência (menor priority) global
                            candidato = None
                            for i, fila in enumerate(self.salas):
                                if fila:
                                    top = fila[0]
                                    if candidato is None or top[0] < candidato[1][0]:
                                        candidato = (i, top)
                            sala_orig, _ = candidato
                            priority, ts, pid, payload = heapq.heappop(self.salas[sala_orig])

                urg = payload.get('urgencia') or payload.get('urgência')
                tempo = TEMPOS_ATENDIMENTO[urg]
                inicio = datetime.utcnow().isoformat() + 'Z'
                espera = (datetime.fromisoformat(inicio[:-1])
                          - datetime.fromisoformat(ts[:-1])).total_seconds()
                time.sleep(tempo)
                fim = datetime.utcnow().isoformat() + 'Z'
                dur = (datetime.fromisoformat(fim[:-1])
                       - datetime.fromisoformat(inicio[:-1])).total_seconds()

                rec = {
                    "pid": pid,
                    "medico": med_id,
                    "room": sala_id,
                    "chegada": ts,
                    "nivel": urg,
                    "inicio": inicio,
                    "saida": fim,
                    "espera": espera,
                    "duracao": dur,
                    "desistencia": False
                }
                with self._log_lock:
                    self.log_event(rec)

                self.stdout.write(
                    f"[{fim}] Méd {med_id}(S{sala_id}) PID{pid} {urg} "
                    f"espera {espera:.1f}s dur {dur:.1f}s"
                )

        # lança N médicos por sala
        for sala in range(n_salas):
            for m in range(1, n_medicos + 1):
                t = threading.Thread(target=medico_thread,
                                     args=(m, sala),
                                     daemon=True)
                t.start()

        # servidor TCP
        with socket.socket() as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen()
            self.stdout.write(f"Escutando em {host}:{port} com {n_salas} salas")
            while True:
                conn, addr = srv.accept()
                with conn:
                    now = datetime.utcnow().isoformat() + 'Z'
                    self.stdout.write(f"[{now}] Conexão de {addr}")
                    raw = conn.recv(1024)
                    try:
                        pay = json.loads(raw.decode())
                    except:
                        continue

                    pid = pay['pid']
                    urg = pay.get('urgencia') or pay.get('urgência')
                    ts = pay['timestamp']

                    # log chegada
                    chegada = {
                        "pid": pid,
                        "medico": None,
                        "room": None,
                        "chegada": ts,
                        "nivel": urg,
                        "inicio": None,
                        "saida": None,
                        "espera": None,
                        "duracao": None,
                        "desistencia": False
                    }
                    with self._log_lock:
                        self.log_event(chegada)

                    # round-robin na sala
                    with self._queue_cv:
                        sala = self._next_sala % n_salas
                        self._next_sala += 1
                        priority = URGENCIA_PRIORIDADES.get(urg, 99)
                        heapq.heappush(self.salas[sala], (priority, ts, pid, pay))
                        self._queue_cv.notify()

                    conn.sendall(b'CHEGADA_RECEBIDA')
