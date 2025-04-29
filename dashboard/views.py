import os
import json
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render

LOG_FILE = os.path.join(settings.BASE_DIR, 'logs.json')
M = getattr(settings, 'MEDICOS', 0)


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
            stats['esperando'] = stats['total'] - stats['atendidos'] + stats['desistencias']
    except (FileNotFoundError, json.JSONDecodeError):
        stats['esperando'] = 0
    return JsonResponse(stats)


def listar_medicos(request):
    """
            GET /api/medicos
            Retorna um JSON { "medicos": [ {id, sala, ocupado}, ... ] }
    """
    medicos = []
    active = {}
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for key, rec in data.items():
            if not key.isdigit():
                continue
            # Paciente em atendimento
            if rec.get('inicio') is not None and rec.get('saida') is None:
                active[rec['medico']] = rec.get('room')
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # Lista completa de médicos
    for mid in range(M):
        medicos.append({
            'id': mid,
            'sala': active.get(mid, '-'),
            'ocupado': mid in active,
        })
    return JsonResponse({'medicos': medicos})


def index(request):
    return render(request, 'dashboard/index.html')
