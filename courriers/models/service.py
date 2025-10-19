from django.db import models
from django.contrib.auth.models import User

class Service(models.Model):
    nom = models.CharField(max_length=100)
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.nom
