import heapq
import threading
import time
import json
from datetime import datetime
from servidor.constants import TIMEOUTS, TEMPOS_ATENDIMENTO, URGENCIA_PRIORIDADES

# Registo global de todas as salas criadas
ROOM_INSTANCES = []


class Room:
    def __init__(self, room_id, num_medicos=5):
        self.room_id = room_id
        self.queue = []
        self.cv = threading.Condition()  # Condiciona a chegada/saida de pacientes
        self.log_lock = threading.Lock()

        ROOM_INSTANCES.append(self)

        # Ativa todos os médicos desta sala
        for m in range(1, num_medicos + 1):
            t = threading.Thread(target=self.medico_worker, args=(m,), daemon=True)
            t.start()

        # Thread de desitência/purge
        t = threading.Thread(target=self.purge_worker, daemon=True)
        t.start()

    def log_event(self, record):
        """Grava eventos logs"""
        try:
            with open('logs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data[str(record['pid'])] = record
        with open('logs.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def purge_worker(self):
        """Desistência dentro desta sala caso o doente espera demasiado"""
        while True:
            time.sleep(1)
            now = datetime.utcnow().isoformat() + 'Z'
            with (self.cv):
                new_queue = []
                for priority, ts, pid, payload in self.queue:
                    level = payload.get('urgencia') or payload.get('urgência')
                    waited = (datetime.fromisoformat(now[:-1]) -
                              datetime.fromisoformat(ts[:-1])
                              ).total_seconds()
                    if waited > TIMEOUTS.get(level, 0):
                        rec = {
                            "pid": pid,
                            "medico": None,
                            "room": self.room_id,
                            "chegada": ts,
                            "nivel": level,
                            "inicio": None,
                            "saida": now,
                            "espera": waited,
                            "duracao": None,
                            "desistencia": True,
                        }
                        with self.log_lock:
                            self.log_event(rec)
                    else:
                        new_queue.append((priority, ts, pid, payload))
                # Reconstroi a pilha para quem não desistiu
                self.queue[:] = new_queue
                heapq.heapify(self.queue)

    def medico_worker(self, med_id):
        """Atende pacientes desta sala"""
        while True:
            with self.cv:
                # Espera paciente na fila
                while not self.queue:
                    self.cv.wait()
                priority, ts, pid, payload = heapq.heappop(self.queue)

            urg = payload.get('urgencia') or payload.get('urgência')
            dur = TEMPOS_ATENDIMENTO.get(urg, 10)
            inicio = datetime.utcnow().isoformat() + 'Z'
            espera = (
                    datetime.fromisoformat(inicio[:-1]) -
                    datetime.fromisoformat(ts[:-1])
            ).total_seconds()

            rec_start = {
                "pid": pid,
                "medico": f"{med_id}",
                "room": self.room_id,
                "chegada": ts,
                "nivel": urg,
                "inicio": inicio,
                "saida": None,
                "espera": espera,
                "duracao": None,
                "desistencia": False
            }

            with self.log_lock:
                self.log_event(rec_start)

            # Simula atendimento
            time.sleep(dur)
            fim = datetime.utcnow().isoformat() + 'Z'
            duracao = (
                    datetime.fromisoformat(fim[:-1]) -
                    datetime.fromisoformat(inicio[:-1])
            ).total_seconds()

            record_end = {
                "pid": pid,
                "medico": f"{med_id}",
                "room": self.room_id,
                "chegada": ts,
                "nivel": urg,
                "inicio": inicio,
                "saida": fim,
                "espera": espera,
                "duracao": duracao,
                "desistencia": False
            }

            with self.log_lock:
                self.log_event(record_end)

            print(f"[Sala {self.room_id}] Médico {med_id} terminou PID {pid} ({urg}) "
                  f"espera {espera:.1f}s, duração {duracao:.1f}s")

    def enqueue(self, pid, ts, payload):
        """Cria a pilha de um novo paciente desta sala"""
        urg = payload.get('urgencia') or payload.get('urgência')
        priority = URGENCIA_PRIORIDADES.get(urg, 99)
        with self.cv:
            heapq.heappush(self.queue, (priority, ts, pid, payload))
            self.cv.notify()


    def size(self):
        """Retorna o tamanho atual da fila"""
        with self.cv:
            return len(self.queue)
