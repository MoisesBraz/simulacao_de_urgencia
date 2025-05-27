from rest_framework import serializers
from simulation_api.models import CommandRun


class CommandRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandRun
        fields = '__all__'