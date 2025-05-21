import os
import json
from json import JSONDecodeError

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

STATUS_FILE = os.path.join(settings.BASE_DIR, 'med_status.json')
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
        with open(STATUS_FILE, 'r', encoding='utf-8') as f:
            status = json.load(f)
    except (FileNotFoundError, JSONDecodeError):
        status= {}
    # Visualiza o num_total de salas do logs
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            meta = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        meta = {}
    TOTAL_SALAS = meta.get('salas_totais', 0)

    # Calcula totais de médicos a partir do status
    TOTAL_MEDICOS = len(status)
    ocupados_med = sum(1 for v in status.values() if v.get('ocupado'))
    livres_med = TOTAL_MEDICOS - ocupados_med

    # Calcula salas ocupadas e livres
    salas_ocupadas = len({ v.get('room') for v in status.values() if v.get('ocupado') })
    salas_livres = max(0, TOTAL_SALAS - salas_ocupadas)

    # Montar lista para envio do front-end
    medicos = []
    for med_key, v in status.items():
        ocupado = bool(v.get('ocupado'))
        sala = v.get('room') if ocupado else None
        medicos.append({
            'id': med_key,
            'sala': sala,
            'ocupado': ocupado,
        })
    resp = {
        'medicos': medicos,
        'medicos_totais': TOTAL_MEDICOS,
        'medicos_livres': livres_med,
        'medicos_ocupados': ocupados_med,
        'salas_totais': TOTAL_SALAS,
        'salas_livres': salas_livres,
        'salas_ocupadas': salas_ocupadas,
    }
    return JsonResponse(resp)


def index(request):
    return render(request, 'dashboard/index.html')
