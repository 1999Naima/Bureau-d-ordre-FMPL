from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from .models import CourrierEntrant
from .forms import CourrierEntrantForm
from .utils.ocr_utils import process_courrier_ocr

@login_required
def add_courrier(request):
    if request.method == 'POST':
        form = CourrierEntrantForm(request.POST, request.FILES)
        if form.is_valid():
            courrier = form.save()
            return redirect('courrier_list')  # Redirect to list view or success page
    else:
        form = CourrierEntrantForm()
    
    return render(request, 'courriers/add_courrier.html', {'form': form})

@method_decorator(csrf_exempt, name='dispatch')
class ProcessOCRView(View):
    def post(self, request):
        if 'courrier_scanné' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'Aucun fichier téléchargé'})
        
        image_file = request.FILES['courrier_scanné']
        lang = request.POST.get('lang', 'ara+fra+eng')  # Get language preference
        
        if not image_file.content_type.startswith('image/'):
            return JsonResponse({'success': False, 'error': 'Le fichier doit être une image'})
        
        extracted_data = process_courrier_ocr(image_file, lang)
        
        if 'error' in extracted_data:
            return JsonResponse({'success': False, 'error': extracted_data['error']})
        
        return JsonResponse({
            'success': True,
            'data': {
                'date': extracted_data['date'].isoformat() if extracted_data['date'] else '',
                'expediteur': extracted_data['expediteur'],
                'objet': extracted_data['objet'],
                'num_ordre': extracted_data['num_ordre'] or '',
                'raw_text': extracted_data['raw_text'],
                'language': extracted_data['language']
            }
        })

# Optional: List view to see all courriers
@login_required
def courrier_list(request):
    courriers = CourrierEntrant.objects.all().order_by('-date')
    return render(request, 'courriers/courrier_list.html', {'courriers': courriers})