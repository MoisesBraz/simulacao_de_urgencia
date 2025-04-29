import os, json, asyncio
from django.conf import settings
from channels.generic.websocket import AsyncWebsocketConsumer

LOG_FILE = os.path.join(settings.BASE_DIR, 'logs.json')


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.last_mtime = None
        # Começa o pooling de background
        self.task = asyncio.create_task(self._poll_logs())

    async def disconnect(self, close_code):
        # Quando o scket é encerrado termina o polling
        self.task.cancel()

    async def _poll_logs(self):
        """Background task: check the JSON file every 2s and push updates."""
        while True:
            try:
                stat = os.stat(LOG_FILE)
                mtime = stat.st_mtime
                if self.last_mtime is None or mtime != self.last_mtime:
                    self.last_mtime = mtime
                    payload = self._load_dashboard_data()
                    await self.send(text_data=json.dumps(payload))
            except FileNotFoundError:
                # Ficheiro de Logs não existe é ignorado
                pass

            await asyncio.sleep(2)

    def _load_dashboard_data(self):
        """Read logs.json and build filas, stats, medicos."""
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        filas = {'verde': 0, 'amarelo': 0, 'vermelho': 0}
        stats = {'atendidos': 0, 'desistencias': 0, 'total': 0}
        M = getattr(settings, 'MEDICOS', 0)
        active_by_med = {}

        # count things
        for key, rec in data.items():
            if not key.isdigit():
                continue
            stats['total'] += 1

            # Estão pacientes a espera
            if rec.get('saida') is None and not rec.get('desistencia', False):
                nivel = rec.get('nivel')
                filas[nivel] += 1
                active_by_med[rec['medico']] = rec['room']
            # desistiram ou foram atendidos
            elif rec.get('desistencia', True):
                stats['desistencias'] += 1
            else:
                stats['atendidos'] += 1

        # build medicos list
        medicos = []
        for mid in range(M):
            ocupado = mid in active_by_med
            medicos.append({
                'id': mid,
                'sala': active_by_med.get(mid),
                'ocupado': ocupado,
            })

        return {
            'filas': filas,
            'stats': stats,
            'medicos': medicos,
        }