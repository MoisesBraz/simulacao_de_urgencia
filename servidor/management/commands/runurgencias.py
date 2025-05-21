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
                            help='Número de salas independentes e médico por cada sala')

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
        n_medicos = n_salas

        # Instancia as salas cada Room cria a sua lógica de fila, médicos e purga
        self.rooms = [
            Room(room_id=i, num_medicos=n_medicos)
            for i in range(n_salas)
        ]
        self._next_sala = 0

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

                    # round-robin: encaminha para a fila da sala correspondente

                    sala = self._next_sala % n_salas
                    self._next_sala += 1
                    self.rooms[sala].enqueue(pid, ts, pay)
                    conn.sendall(b'CHEGADA_RECEBIDA')
