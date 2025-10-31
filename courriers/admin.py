from django.contrib import admin
from django.urls import path
from django.shortcuts import get_object_or_404, render, redirect
from django.utils.html import format_html
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django import forms
from .models import CourrierEntrant, CourrierSortant, Service

class CustomAdminSite(admin.AdminSite):
    def get_urls(self):
        urls = super().get_urls()
        return urls

    def index(self, request, extra_context=None):
        # Get real counts
        extra_context = extra_context or {}
        extra_context.update({
            'total_courriers_entrant': CourrierEntrant.objects.count(),
            'total_courriers_sortant': CourrierSortant.objects.count(),
            'total_services': Service.objects.count(),
        })
        return super().index(request, extra_context)

# Replace default admin site
admin_site = CustomAdminSite(name='custom_admin')

# Import OCR utils avec gestion d'erreur
try:
    from .utils.ocr_utils import process_courrier_ocr
    OCR_AVAILABLE = True
except ImportError as e:
    print(f"Warning: OCR utils not available - {e}")
    OCR_AVAILABLE = False
    def process_courrier_ocr(image_file):
        return {'error': 'OCR non disponible'}

# Admin pour le modèle Service
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'responsable', 'courrier_count']
    list_filter = ['responsable']
    search_fields = ['nom']
    ordering = ['nom']
    
    def courrier_count(self, obj):
        return obj.courrierentrant_set.count() + obj.courriersortant_set.count()
    courrier_count.short_description = 'Nombre de courriers'

# Formulaire pour CourrierSortant avec checkboxes
class CourrierSortantForm(forms.ModelForm):
    class Meta:
        model = CourrierSortant
        fields = '__all__'
        widgets = {
            'services': forms.CheckboxSelectMultiple,
        }

@admin.register(CourrierSortant)
class CourrierSortantAdmin(admin.ModelAdmin):
    form = CourrierSortantForm  # Ajout du formulaire personnalisé
    list_display = ['num_ordre', 'date', 'destination', 'objet_truncated', 'services_display', 'courrier_scanne_link', 'print_action']  # Changé 'service' en 'services_display'
    list_filter = ['date', 'services']  # Changé 'service' en 'services'
    search_fields = ['num_ordre', 'destination', 'objet']
    ordering = ['-date']
    list_per_page = 20
    actions = ['print_selected_action']
    
    # Ajout du fieldset pour les services
    fieldsets = (
        (None, {
            'fields': ('date', 'destination', 'objet', 'num_ordre', 'courrier_scanné', 'services')  # Changé 'service' en 'services'
        }),
    )
    
    def objet_truncated(self, obj):
        return obj.objet[:50] + '...' if len(obj.objet) > 50 else obj.objet
    objet_truncated.short_description = 'Objet'
    
    def services_display(self, obj):
        """Affiche la liste des services dans l'admin"""
        return ", ".join([service.nom for service in obj.services.all()])
    services_display.short_description = 'Services'  # Changé le nom de la colonne
    
    def courrier_scanne_link(self, obj):
        if obj.courrier_scanné:
            return format_html('<a href="{}" target="_blank">🔍</a>', obj.courrier_scanné.url)
        return "-"
    courrier_scanne_link.short_description = 'Fichier'
    
    def print_action(self, obj):
        return format_html(
            '<a href="/admin/courriers/courriersortant/{}/print/" target="_blank">🖨️</a>',
            obj.id
        )
    print_action.short_description = 'Actions'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('print/',
                 self.admin_site.admin_view(self.print_view),
                 name='courriersortant_print_multiple'),
            path('<path:object_id>/print/',
                 self.admin_site.admin_view(self.print_view),
                 name='courriersortant_print'),
            path('process-ocr/',
                 self.admin_site.admin_view(ProcessOCRView.as_view()),
                 name='courriersortant_process_ocr'),
        ]
        return custom_urls + urls
    
    def print_view(self, request, object_id=None):
        """Gère à la fois l'impression individuelle ET multiple"""
        if object_id:
            # Impression individuelle
            courrier = get_object_or_404(CourrierSortant, id=object_id)
            courriers = [courrier]
        else:
            # Impression multiple (depuis l'action de sélection)
            selected_ids = request.GET.getlist('ids')
            if selected_ids:
                courriers = CourrierSortant.objects.filter(id__in=selected_ids)
            else:
                courriers = CourrierSortant.objects.none()
        
        return render(request, 'admin/courriers/print_sortant.html', {'courriers': courriers})
    
    def print_selected_action(self, request, queryset):
        """Action pour imprimer les courriers sortants sélectionnés"""
        selected_ids = queryset.values_list('id', flat=True)
        
        # Construire l'URL avec les IDs sélectionnés
        ids_param = '&'.join([f'ids={id}' for id in selected_ids])
        print_url = f"/admin/courriers/courriersortant/print/?{ids_param}"
        
        # Rediriger vers la page d'impression
        return redirect(print_url)

    print_selected_action.short_description = "🖨️ Imprimer la sélection"
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('services')  # Changé select_related en prefetch_related

class CourrierEntrantForm(forms.ModelForm):
    send_email = forms.BooleanField(
        required=False,
        label="📧 Confirmer l'envoi de l'email",
        help_text="Cocher cette case pour envoyer un email de notification au responsable du service"
    )
    
    class Meta:
        model = CourrierEntrant
        fields = '__all__'
        widgets = {
            'services': forms.CheckboxSelectMultiple,
        }

@admin.register(CourrierEntrant)
class CourrierEntrantAdmin(admin.ModelAdmin):
    form = CourrierEntrantForm
    list_display = ['num_ordre', 'date', 'expediteur', 'objet_truncated', 'services_display', 'courrier_scanne_link', 'print_action', 'email_sent']
    list_filter = ['date', 'services']  # Changé de 'service' à 'services'
    search_fields = ['num_ordre', 'expediteur', 'objet']
    ordering = ['-date']
    actions = ['print_selected_action', 'send_email_action']
    
    # Champs à afficher dans le formulaire
    fieldsets = (
        (None, {
            'fields': ('date', 'expediteur', 'objet', 'num_ordre', 'courrier_scanné', 'services')  # Changé de 'service' à 'services'
        }),
        ('Notification Email', {
            'fields': ('send_email',),
            'classes': ('collapse',),
            'description': 'Envoyer un email au responsable du service lorsque le courrier est enregistré'
        }),
    )
    
    def objet_truncated(self, obj):
        return obj.objet[:50] + '...' if len(obj.objet) > 50 else obj.objet
    objet_truncated.short_description = 'Objet'
    
    def services_display(self, obj):
        """Affiche la liste des services dans l'admin"""
        return ", ".join([service.nom for service in obj.services.all()])
    services_display.short_description = 'Services'  # Changé le nom de la colonne
    
    def courrier_scanne_link(self, obj):
        if obj.courrier_scanné:
            return format_html('<a href="{}" target="_blank">🔍</a>', obj.courrier_scanné.url)
        return "-"
    courrier_scanne_link.short_description = 'Fichier'
    
    def print_action(self, obj):
        return format_html(
            '<a href="/admin/courriers/courrierentrant/{}/print/" target="_blank">🖨️</a>',
            obj.id
        )
    print_action.short_description = 'Actions'
    
    def email_sent(self, obj):
        if hasattr(obj, 'email_sent') and obj.email_sent:
            return format_html('<span style="color: green;">✔</span>')
        return format_html('<span style="color: red;">✘</span>')
    email_sent.short_description = 'Email'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('print/',
                 self.admin_site.admin_view(self.print_view),
                 name='courrierentrant_print_multiple'),
            path('<path:object_id>/print/',
                 self.admin_site.admin_view(self.print_view),
                 name='courrierentrant_print'),
            path('process-ocr/',
                 self.admin_site.admin_view(ProcessOCRView.as_view()),
                 name='courrierentrant_process_ocr'),
            path('<path:object_id>/send-email/',
                 self.admin_site.admin_view(self.send_email_view),
                 name='courrierentrant_send_email'),
        ]
        return custom_urls + urls
    
    def print_view(self, request, object_id=None):
        """Gère à la fois l'impression individuelle ET multiple"""
        if object_id:
            # Impression individuelle
            courrier = get_object_or_404(CourrierEntrant, id=object_id)
            courriers = [courrier]
        else:
            # Impression multiple (depuis l'action de sélection)
            selected_ids = request.GET.getlist('ids')
            if selected_ids:
                courriers = CourrierEntrant.objects.filter(id__in=selected_ids)
            else:
                courriers = CourrierEntrant.objects.none()
        
        return render(request, 'admin/courriers/print_entrant.html', {'courriers': courriers})
    
    def print_selected_action(self, request, queryset):
        """Action pour imprimer les courriers sélectionnés"""
        selected_ids = queryset.values_list('id', flat=True)
        
        # Construire l'URL avec les IDs sélectionnés
        ids_param = '&'.join([f'ids={id}' for id in selected_ids])
        print_url = f"/admin/courriers/courrierentrant/print/?{ids_param}"
        
        # Rediriger vers la page d'impression
        return redirect(print_url)

    print_selected_action.short_description = "🖨️ Imprimer la sélection"
    
    def send_email_action(self, request, queryset):
        """Action pour envoyer des emails pour les courriers sélectionnés"""
        success_count = 0
        for courrier in queryset:
            if self.send_courrier_email(courrier):
                success_count += 1
        
        if success_count > 0:
            messages.success(request, f"Emails envoyés avec succès pour {success_count} courrier(s)")
        else:
            messages.error(request, "Aucun email n'a pu être envoyé")
    
    send_email_action.short_description = "📧 Envoyer un email pour la sélection"
    
    def send_email_view(self, request, object_id):
        """Vue pour envoyer un email pour un courrier spécifique"""
        courrier = get_object_or_404(CourrierEntrant, id=object_id)
        
        if self.send_courrier_email(courrier):
            messages.success(request, f"Email envoyé avec succès pour le courrier {courrier.num_ordre}")
        else:
            messages.error(request, "Erreur lors de l'envoi de l'email")
        
        return redirect(f'/admin/courriers/courrierentrant/{object_id}/change/')
    
    def send_courrier_email(self, courrier):
        """Fonction pour envoyer l'email pour un courrier avec pièce jointe"""
        try:
            # Récupérer tous les services et leurs responsables
            services = courrier.services.all()
            if not services:
                return False
            
            # Collecter tous les emails uniques des responsables
            recipient_emails = []
            for service in services:
                if service.responsable and service.responsable.email:
                    recipient_emails.append(service.responsable.email)
            
            if not recipient_emails:
                return False
            
            # Préparer le contenu de l'email
            service_names = ", ".join([service.nom for service in services])
            
            subject = f"📨 Nouveau courrier entrant - {courrier.num_ordre}"
            message = f"""
            Bonjour,
            
            Un nouveau courrier entrant a été enregistré et assigné à votre/vos service(s).
            
            📋 Détails du courrier :
            • Numéro d'ordre: {courrier.num_ordre}
            • Date: {courrier.date}
            • Expéditeur: {courrier.expediteur}
            • Objet: {courrier.objet}
            • Service(s): {service_names}
            
            Le courrier scanné est joint à cet email.
            
            Cordialement,
            Bureau d'Ordre
            """
            
            from django.core.mail import EmailMessage
            import os
            
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=recipient_emails,
            )
            
            # Vérifier si le fichier existe
            if courrier.courrier_scanné and os.path.exists(courrier.courrier_scanné.path):
                try:
                    file_path = courrier.courrier_scanné.path
                    filename = os.path.basename(file_path)
                    
                    # Lire le fichier en mode binaire
                    with open(file_path, 'rb') as file:
                        file_content = file.read()
                    
                    # Déterminer le type MIME
                    file_extension = filename.split('.')[-1].lower()
                    mime_types = {
                        'pdf': 'application/pdf',
                        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                        'png': 'image/png',
                        'gif': 'image/gif',
                        'tiff': 'image/tiff', 'tif': 'image/tiff',
                        'bmp': 'image/bmp',
                        'doc': 'application/msword',
                        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                    }
                    
                    content_type = mime_types.get(file_extension, 'application/octet-stream')
                    
                    # Attacher le fichier
                    email.attach(filename, file_content, content_type)
                    
                except Exception as file_error:
                    print(f"Erreur lors de l'attachement du fichier: {file_error}")
                    # Ajouter une note dans le message
                    message += "\n\nNote: Le fichier scanné n'a pas pu être joint à cet email."
                    email.body = message
            
            # Envoyer l'email
            email.send(fail_silently=False)
            
            # Marquer que l'email a été envoyé
            courrier.email_sent = True
            if hasattr(courrier, 'save'):
                courrier.save()
            
            return True
            
        except Exception as e:
            print(f"Erreur envoi email: {e}")
            return False
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        # Vérifier si la case d'envoi d'email a été cochée
        if form.cleaned_data.get('send_email') and obj.services.exists():
            if self.send_courrier_email(obj):
                messages.success(request, f"Email envoyé avec succès aux responsables des services")
            else:
                messages.error(request, "Erreur lors de l'envoi des emails aux responsables")

@method_decorator(csrf_exempt, name='dispatch')
class ProcessOCRView(View):
    def post(self, request):
        if not OCR_AVAILABLE:
            return JsonResponse({'success': False, 'error': 'OCR non disponible'})
        
        if 'courrier_scanné' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Aucun fichier téléchargé'})
        
        image_file = request.FILES['courrier_scanné']
        
        if not image_file.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Le fichier doit être une image'})
        
        try:
            extracted_data = process_courrier_ocr(image_file)
            
            if 'error' in extracted_data:
                return JsonResponse({'success': False, 'error': extracted_data['error']})
            
            return JsonResponse({
                'success': True,
                'data': {
                    'date': extracted_data['date'].isoformat() if extracted_data['date'] else '',
                    'expediteur': extracted_data['expediteur'],
                    'objet': extracted_data['objet'],
                    'num_ordre': extracted_data['num_ordre'] or '',
                    'raw_text': extracted_data['raw_text']
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'Erreur OCR: {str(e)}'})