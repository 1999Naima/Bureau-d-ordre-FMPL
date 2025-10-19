from django.db import models
from .service import Service

class CourrierSortant(models.Model):
    date = models.DateField()
    destination = models.CharField(max_length=255)
    objet = models.TextField()
    num_ordre = models.CharField(max_length=50, unique=True)
    courrier_scanné = models.FileField(upload_to='courriers/sortants/')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.num_ordre} - {self.objet[:30]}"
