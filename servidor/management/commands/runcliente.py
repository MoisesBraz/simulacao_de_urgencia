"""
Servidor paciente TCP que chega de forma  autónoma.
A cada execução o cliente espera um intervalo aleatório, ligando ao servidor de urgências,
Envia PID, timestamp e nível de urgência, aguarda a confirmação e termina.
"""
import json
import os
import socket
import threading
from datetime import datetime
from random import uniform, choice
import time
import random
from django.core.management import BaseCommand


class Command(BaseCommand):
    """
        runcliente: simula o processo cliente de urgências.
        Uso:
          python manage.py runcliente [--host HOST] [--port PORT]
    """
    help = 'Inicia um cliente que se conecta ao servidor de urgências, com opção de surto'

    def add_arguments(self, parser):
        parser.add_argument(
            '--host', default='127.0.0.1',
            help='Host do servidor de urgências (padrão 127.0.0.1)'
        )
        parser.add_argument(
            '--port', type=int, default=9000,
            help='Porta TCP do servidor (padrão 9000)'
        )
        parser.add_argument(
            '--min-wait', type=float, default=1.0,
            help='Tempo mínimo de espera antes de chegar (segundos)'
        )
        parser.add_argument(
            '--max-wait', type=float, default=5.0,
            help='Tempo máximo de espera antes de chegar (segundos)'
        )
        parser.add_argument(
            'urgencia', choices=["vermelho", "amarelo", "verde"],
            help='Nível de urgência do paciente'
        )
        parser.add_argument(
            '--surto', type=int, default=0,
            help='Número de clientes para disparar o surto'
        )

    def handle(self, *args, **options):
        host = options['host']
        port = options['port']
        min_wait = options['min_wait']
        max_wait = options['max_wait']
        urgencia = options['urgencia']
        surto = options['surto']

        def send_pacient():
            pid = threading.get_ident()
            wait = random.uniform(min_wait, max_wait)
            time.sleep(wait)
            ts = datetime.utcnow().isoformat() + 'Z'
            try:
                with socket.create_connection((host, port)) as s:
                    payload = {'pid': pid, 'timestamp': ts, 'urgência': urgencia}
                    s.sendall(json.dumps(payload).encode('utf-8'))
                    resp = s.recv(128)
                    print(f"[{pid}] Esperou {wait:.2f}s -> urgências respondeu: {resp!r}")
            except ConnectionRefusedError:
                print(f"[{pid}] Não conseguiu conectar em {host}:{port}")

        if surto:
            threads = []
            for _ in range(surto):
                t = threading.Thread(target=send_pacient)
                t.start()
                threads.append(t)
            for t in threads:
                t.join()
        else:
            send_pacient()
