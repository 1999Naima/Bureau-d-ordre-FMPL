from django.db import models
from courriers.utils.ocr_utils import process_courrier_ocr
from django.core.exceptions import ValidationError

class CourrierEntrant(models.Model):
    date = models.DateField()
    expediteur = models.CharField(max_length=255)
    objet = models.TextField()
    num_ordre = models.CharField(max_length=50, unique=True)
    courrier_scanné = models.FileField(upload_to='courriers/entrants/')
    services = models.ManyToManyField('courriers.Service', blank=True, verbose_name="Services")  # Changé en ManyToMany
    email_sent = models.BooleanField(default=False, verbose_name="Email envoyé") 
    
    def __str__(self):
        return f"{self.num_ordre} - {self.objet[:30]}"

    def save(self, *args, **kwargs):
        # If this is a new instance and a file is being uploaded
        if not self.pk and self.courrier_scanné:
            try:
                # Process the OCR only once when creating the object
                extracted_data = process_courrier_ocr(self.courrier_scanné)
                
                # VÉRIFIER SI extracted_data EST VALIDE
                if extracted_data and isinstance(extracted_data, dict):
                    # Populate fields with extracted data - AVEC VÉRIFICATIONS
                    if extracted_data.get('date') and not self.date:
                        self.date = extracted_data['date']
                    
                    if extracted_data.get('expediteur') and not self.expediteur:
                        self.expediteur = extracted_data['expediteur']
                    
                    if extracted_data.get('objet') and not self.objet:
                        self.objet = extracted_data['objet']
                    
                    if extracted_data.get('num_ordre') and not self.num_ordre:
                        # Check if num_ordre already exists
                        if CourrierEntrant.objects.filter(num_ordre=extracted_data['num_ordre']).exists():
                            raise ValidationError(f"Le numéro d'ordre {extracted_data['num_ordre']} existe déjà.")
                        self.num_ordre = extracted_data['num_ordre']
                
            except Exception as e:
                # Si l'OCR échoue, on continue sans les données extraites
                print(f"Erreur OCR lors de la sauvegarde: {e}")
                # Ne pas lever l'exception pour permettre la sauvegarde du courrier
        
        super().save(*args, **kwargs)