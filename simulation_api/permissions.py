from rest_framework import permissions
from django.conf import settings

class HasAPIKey(permissions.BasePermission):
    """
        Permite acesso apenas se o header X-API-KEY corresponder à chave em settings.API_KEY.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-KEY')
        return bool(api_key and api_key == settings.API_KEY)