import os, subprocess, threading, json

from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import CommandRun
from .serializers import CommandRunSerializer

# Onde se encontra os scripts
BASE_DIR = settings.BASE_DIR

def monitor_process(cmd_run, proc):
    proc.wait()
    cmd_run.sttatus = 'finished' if proc.returncode == 0 else 'error'
    cmd_run.save()

class RunUrgencias(APIView):
    """
        POST /api/runurgencias/
        { "host": "127.0.0.1", "port": 9000, "salas": 3 }
    """
    def post(self, request):
        host = request.data.get('host', '127.0.0.1')
        port = request.data.get('port', 9000)
        salas = request.data.get('salas', 3)
        cmd = [
            'python', 'manage.py', 'runurgencias',
            f'--host={host}', f'--port={port}', f'--salas={salas}'
        ]
        cr = CommandRun.objects.create(
            command='runurgencias',
            args={'host': host, 'port': port, 'salas': salas},
            status='running'
        )
        proc = subprocess.Popen(cmd, cwd=BASE_DIR)
        cr.pid = proc.pid
        cr.save()
        threading.Thread(target=monitor_process, args=(cr, proc), daemon=True).start()
        return Response(CommandRunSerializer(cr).data, status=status.HTTP_201_CREATED)

class RunCliente(APIView):
    """
        POST /api/runcliente/
        { "host":"127.0.0.1", "port":9000, "urgencia":"vermelho", "surto":5 }
    """
    def post(self, request):
        host = request.data.get('host', '127.0.0.1')
        port = request.data.get('port', 9000)
        urgencia = request.data['urgencia']
        surto = request.data.get('surto', 0)
        cmd = [
            'python', 'manage.py', 'runcliente',
            f'--host={host}', f'--port={port}', urgencia, f'--surto={surto}'
        ]
        cr = CommandRun.objects.create(
            command='runcliente',
            args={'host': host, 'port': port, 'urgencia': urgencia, 'surto': surto},
            status='running'
        )
        proc = subprocess.Popen(cmd, cwd=BASE_DIR)
        cr.pid = proc.pid
        cr.save()
        threading.Thread(target=monitor_process, args=(cr, proc), daemon=True).start()
        return Response(CommandRunSerializer(cr).data, status=status.HTTP_201_CREATED)

class SimulateMultiSalas(APIView):
    """
        POST /api/simulate/
        { "salas":3, "pacientes":20, "surto":5 }
    """
    def post(self, request):
        salas = request.data.get('salas', 3)
        pacientes = request.data.get('pacientes', 20)
        surto = request.data.get('surto', 0)
        cmd = [
            'python', 'simulate_multi_salas.py',
            f'--salas={salas}', f'--pacientes={pacientes}', f'--surto={surto}'
        ]
        cr = CommandRun.objects.create(
            command='simulate',
            args={'salas': salas, 'pacientes': pacientes, 'surto': surto},
            status='running'
        )
        proc = subprocess.Popen(cmd, cwd=BASE_DIR)
        cr.pid = proc.pid
        cr.save()
        threading.Thread(target=monitor_process, args=(cr, proc), daemon=True).start()
        return Response(CommandRunSerializer(cr).data, status=status.HTTP_201_CREATED)

class CommandStatus(APIView):
    """
        GET /api/commands/<id>/
    """
    def get(self, request, pk):
        try:
            cr = CommandRun.objects.get(pk=pk)
        except CommandRun.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(CommandRunSerializer(cr).data)

class LogsView(APIView):
    """
       GET /api/logs/
       Retorna conteúdo de logs.json para inspeção do estado dos pacientes.
    """
    def get(self, request):
        logs_path = os.path.join(BASE_DIR, 'logs.json')
        if not os.path.exists(logs_path):
            return Response({"detail": "logs.json não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        with open(logs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return Response(data)

class APIDocumentation(TemplateView):
    """
        Renders a static HTML page com a documentação da API.
    """
    template_name = "api_docs.html"