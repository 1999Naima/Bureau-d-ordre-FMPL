import pytesseract
from PIL import Image
import re
from dateutil import parser
from datetime import datetime
import os

def extract_text_from_image(image_file, lang='fra'):
    """
    Extract text from an image file using Tesseract OCR with French focus
    """
    try:
        # Open image using PIL
        if hasattr(image_file, 'read'):
            if hasattr(image_file, 'seek'):
                image_file.seek(0)
            image = Image.open(image_file)
        else:
            image = Image.open(image_file.path)
        
        # Perform OCR with French language and better configuration
        text = pytesseract.image_to_string(
            image, 
            lang=lang,
            config='--psm 6 -c preserve_interword_spaces=1'
        )
        
        return text.strip()
    
    except Exception as e:
        return f"Error processing image: {str(e)}"

def extract_date(text):
    """
    Extract date from OCR text with better French date parsing
    """
    # French date patterns - improved
    date_patterns = [
        r'le\s+(\d{1,2}\s+[A-Za-zéûàèùâêîôûäëïöüç]+\s+\d{4})',  # "le 3 Juillet 2025"
        r'(\d{1,2}\s+[A-Za-zéûàèùâêîôûäëïöüç]+\s+\d{4})',      # "3 Juillet 2025"
        r'(\d{1,2}/\d{1,2}/\d{4})',  # DD/MM/YYYY
        r'(\d{1,2}-\d{1,2}-\d{4})',  # DD-MM-YYYY
        r'(\d{4}-\d{1,2}-\d{1,2})',  # YYYY-MM-DD
    ]
    
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            try:
                date_str = matches[0]
                # Handle French month names - create a mapping
                month_mapping = {
                    'janvier': 'January', 'février': 'February', 'fevrier': 'February',
                    'mars': 'March', 'avril': 'April', 'mai': 'May', 'juin': 'June',
                    'juillet': 'July', 'août': 'August', 'aout': 'August',
                    'septembre': 'September', 'octobre': 'October',
                    'novembre': 'November', 'décembre': 'December', 'decembre': 'December'
                }
                
                # Replace French month names with English ones
                for fr_month, en_month in month_mapping.items():
                    if fr_month in date_str.lower():
                        date_str = date_str.lower().replace(fr_month, en_month)
                        break
                
                date_obj = parser.parse(date_str, dayfirst=True, fuzzy=True)
                return date_obj.date()
            except (ValueError, TypeError) as e:
                print(f"Date parsing error: {e} for string: {date_str}")
                continue
    
    return None

def extract_expediteur(text):
    """
    Extract sender information specifically for academic/medical French documents
    """
    lines = text.split('\n')
    clean_lines = [line.strip() for line in lines if line.strip()]
    
    # Common academic/medical sender patterns
    academic_patterns = [
        # Faculty/University patterns
        r'Faculté\s+de\s+[A-Z]',
        r'Université\s+[A-Z]',
        r'Département\s+de\s+[A-Z]',
        r'Service\s+de\s+[A-Z]',
        r'CHU\s+[A-Z]',
        r'Hôpital\s+[A-Z]',
        
        # Person titles with academic roles
        r'^(Madame|Monsieur|Mme|M\.)\s+[A-Z][a-z]+\s+[A-Z]',
        r'^Docteur\s+[A-Z]',
        r'^Dr\s+[A-Z]',
        r'^Professeur\s+[A-Z]',
        r'^Pr\s+[A-Z]',
    ]
    
    # Check first 10 lines for academic patterns
    for i, line in enumerate(clean_lines[:10]):
        for pattern in academic_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return line.strip()[:255]
    
    # Look for location + date pattern (common in formal French letters)
    for i, line in enumerate(clean_lines[:5]):
        if re.search(r'[A-Za-zâêîôûäëïöüç]+,\s*le\s+\d+\s+[A-Za-z]+\s+\d{4}', line):
            if ',' in line:
                return line.split(',')[0].strip()[:255]
            return line.strip()[:255]
    
    # Look for lines that contain academic keywords
    academic_keywords = [
        'faculté', 'université', 'médecine', 'medecine', 'pharmacie',
        'hôpital', 'hopital', 'chu', 'service', 'département', 'departement',
        'professeur', 'docteur', 'dr.', 'chef de service'
    ]
    
    for i, line in enumerate(clean_lines[:8]):
        if any(keyword in line.lower() for keyword in academic_keywords):
            return line.strip()[:255]
    
    # Fallback: return the first line that looks formal
    for line in clean_lines:
        if (len(line) > 15 and 
            any(title in line for title in ['Madame', 'Monsieur', 'Mme', 'M.']) and
            not any(word in line.lower() for word in ['objet', 'à', 'a'])):
            return line.strip()[:255]
    
    return "Expéditeur non identifié"

import re

def extract_destination(text):
    """
    Extract destination/recipient information from French documents
    """
    lines = text.split('\n')
    clean_lines = [line.strip() for line in lines if line.strip()]
    
    # Trouver d'abord l'expéditeur pour l'exclure
    expediteur_index = -1
    for i, line in enumerate(clean_lines):
        if any(keyword in line.lower() for keyword in ['faculté', 'université', 'doyen', 'doyenne']):
            expediteur_index = i
            break
    
    # Maintenant chercher le destinataire APRÈS l'expéditeur
    for i, line in enumerate(clean_lines):
        # Pattern pour "A Monsieur..." ou "À Madame..."
        if re.match(r'^[AÀ]\s+(Monsieur|Madame|M\.|Mme|Mlle)', line, re.IGNORECASE):
            # Vérifier que ce n'est pas avant l'expéditeur
            if i > expediteur_index:
                return line.strip()[:255]
        
        # Pattern pour des titres professionnels
        if re.match(r'^(Monsieur|Madame|M\.|Mme|Mlle|Docteur|Dr|Professeur|Pr)\s+', line, re.IGNORECASE):
            # Vérifier que ce n'est pas l'expéditeur et que c'est après lui
            if i > expediteur_index and i > 0:
                if 'faculté' not in clean_lines[i-1].lower() and 'université' not in clean_lines[i-1].lower():
                    return line.strip()[:255]
    
    # Si on n'a pas trouvé, chercher spécifiquement après l'expéditeur
    if expediteur_index != -1:
        for i in range(expediteur_index + 1, len(clean_lines)):
            if re.match(r'^[AÀ]?\s*(Monsieur|Madame|M\.|Mme)', clean_lines[i], re.IGNORECASE):
                return clean_lines[i].strip()[:255]
    
    return "destination non identifié"

def extract_objet(text):
    """
    Extract subject/object information from French documents
    """
    lines = text.split('\n')
    
    # Look for "Objet :" pattern specifically
    for i, line in enumerate(lines):
        if 'objet' in line.lower() and ':' in line:
            # Get text after "Objet :"
            parts = line.split(':', 1)
            if len(parts) > 1 and parts[1].strip():
                return parts[1].strip()
            # If empty, try next line
            elif i + 1 < len(lines) and lines[i + 1].strip():
                return lines[i + 1].strip()
    
    # If no "Objet:" found, look for the line after the recipient
    for i, line in enumerate(lines):
        if line.strip() in ['A', 'À'] and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and 'objet' not in next_line.lower():
                return next_line
    
    return "Objet non spécifié"

def extract_num_ordre(text):
    """
    Extract order number with context awareness for French documents
    """
    lines = text.split('\n')
    
    # Chercher le numéro en début de document (souvent en haut à droite)
    for i, line in enumerate(lines[:5]):  # Regarder les 5 premières lignes
        # Pattern spécifique pour format #####/##
        match = re.search(r'\b(\d{5}/\d{2})\b', line)
        if match:
            return match.group(1)[:50]
        
        # Chercher des numéros entourés d'espaces ou en position isolée
        match = re.search(r'^\s*(\d{4,6}/\d{2})\s*$', line)
        if match:
            return match.group(1)[:50]
    
    # Chercher près de mots-clés comme "N°", "Numéro", "Reference"
    for i, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ['n°', 'numéro', 'no', 'ref', 'réf']):
            # Chercher le pattern spécifique près du mot-clé
            match = re.search(r'\b(\d{5}/\d{2})\b', line)
            if match:
                return match.group(1)[:50]
            
            # Pattern plus général
            match = re.search(r'[\d-/]{6,10}', line)
            if match:
                return match.group()[:50]
    
    # Chercher dans tout le texte en dernier recours
    match = re.search(r'\b(\d{5}/\d{2})\b', text)
    if match:
        return match.group(1)[:50]
    
    return None

def process_courrier_ocr(image_file, lang='fra'):
    """
    Main function to process courrier and extract all fields
    """
    try:
        text = extract_text_from_image(image_file, lang)
        
        if text.startswith("Error"):
            return {'error': text, 'raw_text': ''}
        
        extracted_data = {
            'date': extract_date(text),
            'expediteur': extract_expediteur(text),
            'destination': extract_destination(text),
            'objet': extract_objet(text),
            'num_ordre': extract_num_ordre(text),
            'raw_text': text[:1000] + '...' if len(text) > 1000 else text,
            'language': lang
        }
        
        return extracted_data
    
    except Exception as e:
        return {
            'error': f'Erreur lors du traitement OCR: {str(e)}',
            'date': None,
            'expediteur': '',
            'destination': '',
            'objet': '',
            'num_ordre': '',
            'raw_text': '',
            'language': lang
        }