import socket
import threading
import time
from django.core.management.base import BaseCommand
import heapq
import json
from datetime import datetime

"""
Iniciar servidor TCP de urgências 

Criação do socket TCP, faz bind numa interface e porta configuráveis, 
escuta conexões de pacientes (processos clientes) e envia a confirmação de chegada
"""

URGENCIA_PRIORIDADES = {
    "vermelho": 0,
    "amarelo": 1,
    "verde": 2
}
TEMPOS_ATENDIMENTO = {
    "vermelho": 15,
    "amarelo": 10,
    "verde": 5
}

TIMEOUTS = {
    "vermelho": 240,
    "amarelo": 120,
    "verde": 60
}
MAX_PACIENTES = 20


class Command(BaseCommand):
    """
        Comando 'runurgencias' para ser executado via:
            python manage.py runurgencias [--host HOST] [--port PORT]

        Parâmetros:
        --host:  interface de rede onde o servidor ficará a escutar localhost.
        --port:  número de porta TCP para escuta (padrão 9000).
    """

    help = "Servidor de urgencias: fila, surtos, desistências e logs JSON"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #  A fila interna: cada item é (prioridade, timestamp, pid, payload)
        self.triage_queue = []
        # sincronização de váriaveis
        self._queue_lock = threading.Lock()
        self._queue_cv = threading.Condition(self._queue_lock)
        self._log_lock = threading.Lock()

    def add_arguments(self, parser):
        parser.add_argument('--host', default='127.0.0.1',
                            help='Host listen server default 127.0.0.1')
        parser.add_argument('--port', type=int, default=9000,
                            help='Port TCP para escutar default 9000')

    # Definição para registar logs no ficheiro logs.json por PID
    def log_event(self, record):
        """
            Lê o logs.json (ou cria um dicionário vazio),
            actualiza/inserir o record pelo PID e regrava tudo em logs.json.
        """
        try:
            with open('logs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}

        data[str(record['pid'])] = record

        with open('logs.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def handle(self, *args, **options):
        """
            Ponto de entrada do comando. Configura o socket, entra em loop de
            aceitação de conexões e responde a cada cliente.
        """
        host = options['host']
        port = options['port']

        # Thread de gestão das desistências
        def purge_thread():
            while True:
                time.sleep(1)
                date_now = datetime.utcnow().isoformat() + 'Z'
                with self._queue_cv:
                    restante = []
                    for priority, ts, pid, payload in self.triage_queue:
                        nivel = payload.get('urgencia') or payload.get('urgência')
                        waited = (
                                datetime.fromisoformat(date_now[:-1])
                                - datetime.fromisoformat(ts[:-1])
                        ).total_seconds()
                        # Ultrapassa o timeout regista a desitência
                        if waited > TIMEOUTS.get(nivel, 0):
                            record = {
                                "pid": pid,
                                "medico": None,
                                "chegada": ts,
                                "nivel": nivel,
                                "inicio": None,
                                "saida": date_now,
                                "espera": waited,
                                "duracao": None,
                                "desistencia": True
                            }
                            with self._log_lock:
                                self.log_event(record)
                        else:
                            restante.append((priority, ts, pid, payload))
                    # Reconstroi a fila sem a desistência
                    self.triage_queue[:] = restante
                    heapq.heapify(self.triage_queue)

        threading.Thread(target=purge_thread, daemon=True).start()

        # Thread para cada médico
        def medico_thread(med_id):
            while True:
                with self._queue_cv:
                    while not self.triage_queue:
                        self._queue_cv.wait()
                    priority, ts_chegada, pid, payload = heapq.heappop(self.triage_queue)
                urg = payload.get('urgencia') or payload.get('urgência')
                atendimento = TEMPOS_ATENDIMENTO.get(urg, 10)

                # registar o inicio do atendimento
                inicio_ts = datetime.utcnow().isoformat() + 'Z'
                espera_s = (
                        datetime.fromisoformat(inicio_ts[:-1]) -
                        datetime.fromisoformat(ts_chegada[:-1])
                ).total_seconds()
                # simula o atendimento
                time.sleep(atendimento)
                # Regista o fim do atendimento
                fim_ts = datetime.utcnow().isoformat() + 'Z'
                duracao = (
                        datetime.fromisoformat(fim_ts[:-1]) -
                        datetime.fromisoformat(inicio_ts[:-1])
                ).total_seconds()
                # Registar chegada, inicio, espera, fim, duração
                record = {
                    "pid": pid,
                    "medico": med_id,
                    "chegada": ts_chegada,
                    "nivel": urg,
                    "inicio": inicio_ts,
                    "saida": fim_ts,
                    "espera": espera_s,
                    "duracao": duracao,
                    "desistencia": False
                }
                with self._log_lock:
                    self.log_event(record)
                self.stdout.write(
                    f"[{fim_ts}] Médico {med_id} terminou PID {pid} ({urg}); "
                    f"Espera {espera_s:.1f}s, duração {duracao:.1f}s"
                )

        # Ativa/Lança as 5 threads de médicos
        for i in range(1, 6):
            t = threading.Thread(target=medico_thread, args=(i,), daemon=True)
            t.start()

        # Cria servidor TCP
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((host, port))
            srv.listen()
            self.stdout.write(f'Servidor de urgências escutando em {host}:{port}')

            # Aceitar n clientes
            while True:
                conn, addr = srv.accept()
                with conn:
                    now = datetime.utcnow().isoformat() + 'Z'
                    self.stdout.write(f'[{now}] Conexão de {addr}')

                    data = conn.recv(1024)

                    # --- TRIAGEM ---
                    try:
                        payload = json.loads(data.decode('utf-8'))
                    except json.JSONDecodeError:
                        self.stderr.write('JSON inválido; ignora cliente.')
                        continue

                    # extrai campos
                    urg = payload.get('urgencia') or payload.get('urgência')
                    pid = payload.get('pid')
                    ts = payload.get('timestamp')

                    # Log de chegada
                    arrival_record = {
                        "pid": pid,
                        "medico": None,
                        "chegada": ts,
                        "nivel": urg,
                        "inicio": None,
                        "saida": None,
                        "espera": None,
                        "duracao": None,
                        "desistencia": False
                    }
                    with self._log_lock:
                        self.log_event(arrival_record)

                    # Adiciona à fila de triagem
                    priority = URGENCIA_PRIORIDADES.get(urg, 99)
                    with self._queue_cv:
                        heapq.heappush(self.triage_queue, (priority, ts, pid, payload))
                        # Chama um médico
                        self._queue_cv.notify()

                    # Imprime a fila atual
                    self.stdout.write('--- Fila de Espera (urgência ↓) ---')
                    for p, t_stamp, p_id, _ in self.triage_queue:
                        nome = next(k for k, v in URGENCIA_PRIORIDADES.items() if v == p)
                        self.stdout.write(f'   PID {p_id:5d} | {nome:8s} | chegada {t_stamp}')
                    self.stdout.write('-----------------------------------')

                    # Envia confirmação que a chegada foi recebida
                    conn.sendall(b'CHEGADA_RECEBIDA')
