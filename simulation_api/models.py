from django.db import models

class CommandRun(models.Model):
    COMMAND_CHOICES = [
        ('runurgencias', 'Run Urgencias'),
        ('runcliente', 'Run Cliente'),
        ('simulate', 'Simulate Multi Salas'),
    ]
    command = models.CharField(max_length=20, choices=COMMAND_CHOICES)
    pid = models.IntegerField(null=True, blank=True)
    args = models.JSONField()
    status = models.CharField(max_length=20, default='running')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.command} [{self.id}] - {self.status}"
