from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from .models.courrier_entrant import CourrierEntrant

@receiver(post_save, sender=CourrierEntrant)
def notifier_responsable_service(sender, instance, created, **kwargs):
    service = instance.service
    if service and service.responsable and service.responsable.email:
        sujet = f"Nouveau courrier affecté au service {service.nom}"
        message = f"""
        Bonjour {service.responsable.username},

        Un nouveau courrier vous a été attribué :
        - Objet : {instance.objet}
        - Numéro d'ordre : {instance.num_ordre}
        - Expéditeur : {instance.expediteur}
        - Date : {instance.date}

        Merci de consulter l'application.
        """
        send_mail(
            sujet,
            message,
            'noreply@votresite.com',
            [service.responsable.email],
            fail_silently=False,
        )
