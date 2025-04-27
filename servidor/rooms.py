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
        self.cv = threading.Condition() # Condiciona a chegada/saida de pacientes
        self.log_lock = threading.Lock()

        ROOM_INSTANCES.append(self)

        # Ativa todos os médicos desta sala
        for m in range(1, num_medicos+1):
            t = threading.Thread(target=self.medico_worker, args=(m,), daemon=True)
            t.start()

        # Thread de desitência
        t = threading.Thread(target=self.purge_worker, daemon=True)
        t.start()

    def log_event(self, record):
        """Grava eventos logs"""
        try:
            with open('logs.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {}
        data[f"{record['pid']}"] = record
        with open('logs.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def purge_worker(self):
        """Desistência dentro desta sala caso o doente espera demasiado tempo nesta sala"""
        while True:
            time.sleep(1)
            now = datetime.utcnow().isoformat() + 'Z'
            with self.cv:
                new = []
                for priority, ts, pid, payload in self.queue:
                    level = payload.get('urgencia') or payload.get('urgência')
                    waited = (datetime.fromisoformat(now[:-1]) -
                              datetime.fromisoformat(ts[:-1])).total_seconds()
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
                        new.append((priority, ts, pid, payload))
                # Reconstroi a pilha para quem não desistiu
                self.queue[:] = new
                heapq.heapify(self.queue)
    def medico_worker(self, med_id):
        """atende pacientes desta sala e, se vazio, tenta casos críticos de fora"""
        while True:
            with self.cv:
                # Espera de alguém nesta sala
                while not self.queue:
                    self.cv.wait(timeout=2)
                    if self.queue:
                        break
                if self.queue:
                    # Atende os próprios pacientes da sala
                    priority, ts, pid, payload = heapq.heappop(self.queue)
                else:
                    # Emprestimo de pacientes criticos de outras salas
                    emprest = self.find_critical_elsewhere()
                    if emprest:
                        _, (priority, ts, pid, payload) = emprest
                    else:
                        # Rouba Pacientes mais urgentes dentro de todas as salas
                        candidato = None
                        for room in ROOM_INSTANCES:
                            if room.queue:
                                top = room.queue[0]
                                if (candidato is None) or (top[0] < candidato[1][0]):
                                    candidato = (room, top)
                        room_origem, _ = candidato
                        priority, ts, pid, payload = heapq.heappop(room_origem.queue)

            # Simula o atendimento
            urg = payload.get('urgencia') or payload.get('urgência')
            dur = TEMPOS_ATENDIMENTO.get(urg, 10)
            inicio = datetime.utcnow().isoformat() + 'Z'
            espera = (datetime.fromisoformat(inicio[:-1]) -
                      datetime.fromisoformat(ts[:-1])).total_seconds()
            time.sleep(dur)
            fim = datetime.utcnow().isoformat() + 'Z'
            duracao = (datetime.fromisoformat(fim[:-1]) -
                       datetime.fromisoformat(inicio[:-1])).total_seconds()
            record = {
                "pid": pid,
                "medico": f"{self.room_id}-{med_id}",
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
                self.log_event(record)
            print(f"[Sala {self.room_id}] Médico {med_id} terminou PID {pid} ({urg}) "
                  f"espera {espera:.1f}s, duração {duracao:.1f}s")

    def find_critical_elsewhere(self):
        """Procura outras salas um paciente crítico com prioridade 0/vermelho. Se encontrar retira o heap e retorna (sala_id, tupla do paciente)"""
        for room in ROOM_INSTANCES:
            if room is self:
                continue
            with room.cv:
                if room.queue and room.queue[0][0] == 0:
                    paciente = heapq.heappop(room.queue)
                    heapq.heapify(room.queue)
                    return room.room_id, paciente
        return None

    def enqueue(self, pid, ts, payload):
        """Chamada externa para chegar um novo paciente"""
        urg = payload.get('urgencia') or payload.get('urgência')
        priority = URGENCIA_PRIORIDADES.get(urg, 99)
        with self.cv:
            heapq.heappush(self.queue, (priority, ts, pid, payload))
            self.cv.notify()

    def size(self):
        """Retorna o tamanho da fila"""
        with self.cv:
            return len(self.queue)