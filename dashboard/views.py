import os
import json
from json import JSONDecodeError

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

LOG_FILE = os.path.join(settings.BASE_DIR, 'logs.json')

def estado_filas(request):
    """
        GET /api/filas/
        { 'verde': n1, 'amarelo': n2, 'vermelho': n3 }
        Apenas conta quem ainda não saiu nem desistiu.
    """
    filas = {'verde': 0, 'amarelo': 0, 'vermelho': 0}
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for rec in data.values():
            # Só pacientes em espera
            if isinstance(rec, dict) and rec.get('saida') is None and not rec.get('desistencia', False):
                nivel = rec.get('nivel')
                filas[nivel] += 1
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return JsonResponse(filas)


def estatisticas(request):
    """
        GET /api/stats/
        { 'atendidos': x, 'desistencias': y, 'total': z }
    """
    stats = {'atendidos': 0, 'desistencias': 0, 'total': 0}
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, rec in data.items():
            if not key.isdigit():
                continue
            stats['total'] += 1
            if rec.get('desistencia', False):
                stats['desistencias'] += 1
            elif rec.get('saida') is not None:
                stats['atendidos'] += 1
            stats['esperando'] = stats['total'] - (stats['atendidos'] + stats['desistencias'])
    except (FileNotFoundError, json.JSONDecodeError):
        stats['esperando'] = 0
    return JsonResponse(stats)


def listar_medicos(request):
    """
        GET /api/medicos
        Retorna um JSON
        {
            "medicos": [ {id, sala, ocupado}, ... ],
            'medicos_totais':   int
            'medicos_livres':   int
            'medicos_ocupados': int
            'salas_totais':     int
            'salas_livres':     int
            'salas_ocupadas':   int
        }
    """
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, JSONDecodeError):
        data = {}

    TOTAL_MEDICOS = data.get('medicos_totais', 0)
    TOTAL_SALAS = data.get('salas_totais', 0)

    # Constroi dicinário de médico
    medico_sala = {}
    for rec in data.values():
        if not isinstance(rec, dict):
            continue
        # Consulta em andamento
        if rec.get('inicio') and not rec.get('saida'):
            medico = rec.get('medico')
            sala = rec.get('room')
            if medico and sala:
                medico_sala[medico] = sala

    ocupados_med = len(medico_sala)
    livres_med = max(0, TOTAL_MEDICOS - ocupados_med)
    ocupadas_sal = len(set(medico_sala.values()))
    livres_sal = max(0, TOTAL_SALAS - ocupadas_sal)

    # Montar lista para envio do front-end
    medicos = []
    for mid in range(1, TOTAL_MEDICOS + 1):
        medicos.append({
            'id': mid,
            'sala': medico_sala.get(mid, '-'),
            'ocupado': mid in medico_sala,
        })

    resp = {
        'medicos': medicos,
        'medicos_totais': TOTAL_MEDICOS,
        'medicos_livres': livres_med,
        'medicos_ocupados': ocupados_med,
        'salas_totais': TOTAL_SALAS,
        'salas_livres': livres_sal,
        'salas_ocupadas': ocupadas_sal,
    }
    return JsonResponse(resp)


def index(request):
    return render(request, 'dashboard/index.html')
