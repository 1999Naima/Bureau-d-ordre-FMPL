from django import forms
from .models import CourrierEntrant, CourrierSortant, Service
from .utils.ocr_utils import process_courrier_ocr

class CourrierEntrantForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Services"
    )
    
    class Meta:
        model = CourrierEntrant
        fields = ['date', 'expediteur', 'objet', 'num_ordre', 'courrier_scanné', 'services', 'email_sent']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expediteur': forms.TextInput(attrs={'class': 'form-control'}),
            'objet': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'num_ordre': forms.TextInput(attrs={'class': 'form-control'}),
            'courrier_scanné': forms.FileInput(attrs={'class': 'form-control'}),
            'email_sent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class CourrierSortantForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        label="Services"
    )
    
    class Meta:
        model = CourrierSortant
        fields = ['date', 'destination', 'objet', 'num_ordre', 'courrier_scanné', 'services']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'destination': forms.TextInput(attrs={'class': 'form-control'}),
            'objet': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'num_ordre': forms.TextInput(attrs={'class': 'form-control'}),
            'courrier_scanné': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required since they'll be auto-filled
        self.fields['date'].required = False
        self.fields['destination'].required = False
        self.fields['objet'].required = False
        self.fields['num_ordre'].required = False

    def clean(self):
        cleaned_data = super().clean()
        courrier_scanné = cleaned_data.get('courrier_scanné')
        
        if courrier_scanné and not self.instance.pk:  # Only for new instances
            # Process OCR to validate and suggest data
            extracted_data = process_courrier_ocr(courrier_scanné)
            
            if extracted_data:
                # Suggest values if fields are empty
                if not cleaned_data.get('date') and extracted_data['date']:
                    self.cleaned_data['date'] = extracted_data['date']
                
                if not cleaned_data.get('destination') and extracted_data['expediteur']:
                    self.cleaned_data['destination'] = extracted_data['expediteur']
                
                if not cleaned_data.get('objet') and extracted_data['objet']:
                    self.cleaned_data['objet'] = extracted_data['objet']
                
                if not cleaned_data.get('num_ordre') and extracted_data['num_ordre']:
                    self.cleaned_data['num_ordre'] = extracted_data['num_ordre']
        
        return cleaned_data