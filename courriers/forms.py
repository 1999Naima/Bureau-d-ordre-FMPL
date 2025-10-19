from django import forms
from .models import CourrierEntrant
from .utils.ocr_utils import process_courrier_ocr

class CourrierEntrantForm(forms.ModelForm):
    class Meta:
        model = CourrierEntrant
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'expediteur': forms.TextInput(attrs={'class': 'form-control'}),
            'objet': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'num_ordre': forms.TextInput(attrs={'class': 'form-control'}),
            'courrier_scanné': forms.FileInput(attrs={'class': 'form-control'}),
            'service': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields not required since they'll be auto-filled
        self.fields['date'].required = False
        self.fields['expediteur'].required = False
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
                
                if not cleaned_data.get('expediteur') and extracted_data['expediteur']:
                    self.cleaned_data['expediteur'] = extracted_data['expediteur']
                
                if not cleaned_data.get('objet') and extracted_data['objet']:
                    self.cleaned_data['objet'] = extracted_data['objet']
                
                if not cleaned_data.get('num_ordre') and extracted_data['num_ordre']:
                    self.cleaned_data['num_ordre'] = extracted_data['num_ordre']
        
        return cleaned_data