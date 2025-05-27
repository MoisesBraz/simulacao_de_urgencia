import os
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

MED_STATUS_FILE = 'med_status.json'
LOG_FILE = 'logs.json'

"""
Iniciar servidor TCP de urgências 

Criação do socket TCP, faz bind numa interface e porta configuráveis, 
escuta conexões de pacientes (processos clientes) e envia a confirmação de chegada
"""


class Command(BaseCommand):
    help = "Servidor de urgencias com multi-salas e múltiplos médicos por sala."

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=9000)
        parser.add_argument('--salas', type=int, default=3,
                            help='Número de salas independentes')
        parser.add_argument('--medicos', type=int, default=1,
                            help='Número de médicos por sala')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Lock único para todas as escritas em logs.json
        self._log_lock = threading.Lock()

    def log_event(self, record):
        """Grava um registo em logs.json."""
        with self._log_lock:
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            data[str(record['pid'])] = record
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def handle(self, *args, **opts):
        host = opts['host']
        port = opts['port']
        n_salas = opts['salas']
        n_medicos = opts['medicos']

        # Limpa med_status.json de execuções anteriores
        if os.path.exists(MED_STATUS_FILE):
            os.remove(MED_STATUS_FILE)

        # Recria med_status.json com todos os médicos (ocupado=False)
        initial = {
            f"{room_id}-{med_id}": {'room': room_id, 'ocupado': False}
            for room_id in range(n_salas)
            for med_id in range(1, n_medicos + 1)
        }
        with open(MED_STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(initial, f, ensure_ascii=False, indent=2)

        # Instancia as Room e inicia threads de médicos e purge
        self.rooms = [
            Room(room_id=i, num_medicos=n_medicos, log_lock=self._log_lock)
            for i in range(n_salas)
        ]
        self._next_sala = 0

        # Servidor TCP
        with socket.socket() as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen()
            self.stdout.write(
                f"Escutando em {host}:{port} com "
                f"{n_salas} salas e {n_medicos} médicos/sala"
            )
            while True:
                conn, addr = srv.accept()
                with conn:
                    now = datetime.utcnow().isoformat() + 'Z'
                    self.stdout.write(f"[{now}] Conexão de {addr}")
                    raw = conn.recv(1024)
                    try:
                        pay = json.loads(raw.decode())
                    except json.JSONDecodeError:
                        continue

                    pid = pay['pid']
                    urg = pay.get('urgencia') or pay.get('urgência')
                    ts = pay['timestamp']

                    # Log de chegada
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
                    self.log_event(chegada)

                    # Round-robin para escolher sala e enfileirar
                    sala = self._next_sala % n_salas
                    self._next_sala += 1
                    self.rooms[sala].enqueue(pid, ts, pay)

                    # Confirma chegada ao cliente
                    conn.sendall(b'CHEGADA_RECEBIDA')
