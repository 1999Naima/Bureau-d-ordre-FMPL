# courriers/models/courrier_sortant.py
from django.db import models
from django.core.exceptions import ValidationError
from .service import Service
import os

class CourrierSortant(models.Model):
    date = models.DateField()
    destination = models.CharField(max_length=255)
    objet = models.TextField()
    num_ordre = models.CharField(max_length=50, unique=True)
    courrier_scanné = models.FileField(upload_to='courriers/sortants/')
    services = models.ManyToManyField(Service, blank=True, verbose_name="Services")

    def __str__(self):
        return f"{self.num_ordre} - {self.objet[:30]}"

    def save(self, *args, **kwargs):
        # Import ici pour éviter les imports circulaires
        from courriers.utils.ocr_utils import process_courrier_ocr
        
        # If this is a new instance and a file is being uploaded
        if not self.pk and self.courrier_scanné:
            try:
                # Vérifier que le fichier existe et est accessible
                if hasattr(self.courrier_scanné, 'path') and os.path.exists(self.courrier_scanné.path):
                    # Process the OCR only once when creating the object
                    extracted_data = process_courrier_ocr(self.courrier_scanné)
                    
                    # VÉRIFICATION ROBUSTE : s'assurer que extracted_data est un dict valide
                    if extracted_data and isinstance(extracted_data, dict) and extracted_data != {}:
                        
                        # Populate fields with extracted data - AVEC VÉRIFICATIONS COMPLÈTES
                        if extracted_data.get('date') and not self.date:
                            self.date = extracted_data['date']
                        
                        if extracted_data.get('destination') and not self.destination:
                            self.destination = extracted_data['destination']
                        
                        if extracted_data.get('objet') and not self.objet:
                            self.objet = extracted_data['objet']
                        
                        if extracted_data.get('num_ordre') and not self.num_ordre:
                            # Check if num_ordre already exists
                            if CourrierSortant.objects.filter(num_ordre=extracted_data['num_ordre']).exists():
                                # Juste un warning, ne pas bloquer la sauvegarde
                                print(f"Attention: Le numéro d'ordre {extracted_data['num_ordre']} existe déjà.")
                            else:
                                self.num_ordre = extracted_data['num_ordre']
                    else:
                        print("Aucune donnée valide extraite par OCR")
                
            except Exception as e:
                # Si l'OCR échoue, on continue sans les données extraites
                print(f"Erreur OCR lors de la sauvegarde du courrier sortant: {e}")
                # Ne pas lever l'exception pour permettre la sauvegarde du courrier
        
        super().save(*args, **kwargs)