from django.db import models
from .service import Service

class CourrierSortant(models.Model):
    date = models.DateField()
    destination = models.CharField(max_length=255)
    objet = models.TextField()
    num_ordre = models.CharField(max_length=50, unique=True)
    courrier_scanné = models.FileField(upload_to='courriers/sortants/')
    services = models.ManyToManyField(Service, blank=True, verbose_name="Services")  # Changé en ManyToMany

    def __str__(self):
        return f"{self.num_ordre} - {self.objet[:30]}"