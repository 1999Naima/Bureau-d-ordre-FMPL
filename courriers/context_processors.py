# your_app/context_processors.py
from .models import CourrierEntrant, CourrierSortant, Service

def dashboard_stats(request):
    if request.path == '/admin/':
        total_courriers_entrant = CourrierEntrant.objects.count()
        total_courriers_sortant = CourrierSortant.objects.count()
        total_services = Service.objects.count()
        
        return {
            'total_courriers_entrant': total_courriers_entrant,
            'total_courriers_sortant': total_courriers_sortant,
            'total_services': total_services,
        }
    return {}