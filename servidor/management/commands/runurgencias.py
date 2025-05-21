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
LOG_FILE        = 'logs.json'

"""
Iniciar servidor TCP de urgências 

Criação do socket TCP, faz bind numa interface e porta configuráveis, 
escuta conexões de pacientes (processos clientes) e envia a confirmação de chegada
"""


class Command(BaseCommand):
    help = "Servidor de urgencias com multi-salas 1 médico por sala. "

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=9000)
        parser.add_argument('--salas', type=int, default=3,
                            help='Número de salas independentes e médico por cada sala')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._log_lock = threading.Lock()

    def log_event(self, record):
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
        n_medicos = 1

        if not os.path.exists(MED_STATUS_FILE):
            initial = {
                f"{room_id}-{med_id}": {'room': room_id, 'ocupado': False}
                for room_id in range(n_salas)
                for med_id in range(1, n_medicos + 1)
            }
            with open(MED_STATUS_FILE, 'w', encoding='utf-8') as f:
                json.dump(initial, f, ensure_ascii=False, indent=2)

        # Instância as salas cada Room cria a sua lógica de fila, médicos e purga
        self.rooms = [
            Room(room_id=i, num_medicos=n_medicos)
            for i in range(n_salas)
        ]
        self._next_sala = 0

        # Inicializa o med_status.json
        initial = {}
        for room in self.rooms:
            # Cada sala = 1 médico cujo key é "salaID-medID"
            med_key = f"{room.room_id}-1"
            initial[med_key] = {'room': room.room_id, 'ocupado': False}
        with open('med_status.json', 'w', encoding='utf-8') as f:
            json.dump(initial, f, ensure_ascii=False, indent=2)

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
