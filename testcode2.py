import streamlit as st
import tempfile
import base64
import requests
import PyPDF2
import io
import docx
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from streamlit_option_menu import option_menu
import streamlit as st
import os
from dotenv import load_dotenv

# Configuration de la page
st.set_page_config(
    page_title="Assistant IA - Générateur des Cas de test",
    page_icon="📋",
    layout="wide"
)

# Essayer de charger depuis .env pour le développement local
load_dotenv()

# Récupérer la clé API (priorité aux secrets Streamlit)
def get_api_key():
    # D'abord chercher dans les secrets Streamlit (production)
    if 'ANTHROPIC_API_KEY' in st.secrets:
        return st.secrets['ANTHROPIC_API_KEY']
    # Sinon chercher dans les variables d'environnement (dev local)
    else:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            st.error("Clé API Anthropic non trouvée. Vérifiez votre configuration.")
        return api_key
        
# Fonction pour extraire le texte d'un fichier DOCX
def extract_text_from_docx(file):
    doc = docx.Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def extract_text_from_pdf(file):
    pdf_reader = PyPDF2.PdfReader(io.BytesIO(file.read()))
    text = []
    for page in pdf_reader.pages:
        text.append(page.extract_text())
    return "\n".join(text)

# Fonction pour créer un lien de téléchargement
def create_download_link(file_data, file_type, file_name):
    b64 = base64.b64encode(file_data).decode()
    
    if file_type == "pdf":
        href = f'<a href="data:application/pdf;base64,{b64}" download="{file_name}" class="css-1offfwp edgvbvh9" style="background-color: #0066cc; color: white; font-weight: bold; padding: 0.5rem; border-radius: 0.25rem; text-decoration: none; width: 100%; display: inline-block; text-align: center;">Télécharger en PDF</a>'
    else:
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.wordprocessingml.document;base64,{b64}" download="{file_name}" class="css-1offfwp edgvbvh9" style="background-color: #0066cc; color: white; font-weight: bold; padding: 0.5rem; border-radius: 0.25rem; text-decoration: none; width: 100%; display: inline-block; text-align: center;">Télécharger en DOCX</a>'
    
    return href
# Fonction pour créer un PDF bien structuré à partir du texte
def create_pdf(output_text, filename="cas_de_test.pdf"):
    buffer = io.BytesIO()
    
    # Définition des marges et de la taille
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=letter,
        rightMargin=60,
        leftMargin=60,
        topMargin=72,
        bottomMargin=60
    )
    
    # Styles améliorés
    styles = getSampleStyleSheet()
    
    # Style du titre principal
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=22,
        textColor=colors.darkblue,
        spaceAfter=20,
        alignment=TA_CENTER,
        borderWidth=0,
        borderPadding=10,
        leading=30
    )
    
    # Style pour les titres de sections
    heading2_style = ParagraphStyle(
        'Heading2',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.darkblue,
        spaceAfter=12,
        spaceBefore=12,
        borderBottom=1,
        borderColor=colors.darkblue,
        paddingBottom=5,
        leading=20
    )
    
    # Style pour les scénarios
    heading3_style = ParagraphStyle(
        'Heading3',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.navy,
        spaceAfter=8,
        spaceBefore=8,
        leading=16,
        bulletIndent=0
    )
    
    # Style pour le texte normal
    normal_style = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_JUSTIFY,
        leading=16,  # Espacement entre les lignes
        firstLineIndent=0
    )
    
    # Style pour les préconditions
    precondition_style = ParagraphStyle(
        'Precondition',
        parent=normal_style,
        leftIndent=20,
        textColor=colors.black
    )
    
    # Style pour les étapes
    steps_style = ParagraphStyle(
        'Steps',
        parent=normal_style,
        leftIndent=20,
        textColor=colors.black
    )
    
    # Style pour les résultats attendus
    result_style = ParagraphStyle(
        'Result',
        parent=normal_style,
        leftIndent=20,
        textColor=colors.black,
        backColor=colors.lightgrey,
        borderPadding=5
    )
    
    # Style pour la date
    date_style = ParagraphStyle(
        'Date',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    flowables = []
    
    # Page de titre
    flowables.append(Paragraph("Cas de Test", title_style))
    flowables.append(Spacer(1, 0.3*inch))
    
    # Date de génération
    from datetime import datetime
    date_str = datetime.now().strftime("Généré le %d/%m/%Y à %H:%M")
    flowables.append(Paragraph(date_str, date_style))
    flowables.append(Spacer(1, 0.5*inch))
    
    # Splitter le texte en sections et paragraphes
    lines = output_text.split('\n')
    current_section = []
    in_precondition = False
    in_steps = False
    in_result = False
    
    for line in lines:
        # Gestion des sections principales (exigences)
        if line.startswith('## ') or line.startswith('**EXIGENCE ') or (line.startswith('EXIGENCE ') and not line.startswith('EXIGENCE:')):
            # Si on a une section précédente, on la traite
            if current_section:
                section_text = '\n'.join(current_section)
                para = Paragraph(section_text.replace('\n', '<br/>'), normal_style)
                flowables.append(para)
                flowables.append(Spacer(1, 0.15*inch))
                current_section = []
            
            # Nouvelle section avec saut de page
            flowables.append(PageBreak())
            
            # Titre de la section (exigence)
            if line.startswith('## '):
                flowables.append(Paragraph(line[3:], heading2_style))
            else:
                if line.startswith('**EXIGENCE '):
                    clean_line = line.replace('**', '')
                else:
                    clean_line = line
                flowables.append(Paragraph(clean_line, heading2_style))
                
        # Gestion des scénarios
        elif line.startswith('**Scenario ') or line.startswith('Scenario ') or line.startswith('**Cas '):
            # Si on a une section précédente, on la traite
            if current_section:
                section_text = '\n'.join(current_section)
                
                # Appliquer le style approprié
                if in_precondition:
                    style_to_use = precondition_style
                    in_precondition = False
                elif in_steps:
                    style_to_use = steps_style
                    in_steps = False
                elif in_result:
                    style_to_use = result_style
                    in_result = False
                else:
                    style_to_use = normal_style
                
                para = Paragraph(section_text.replace('\n', '<br/>'), style_to_use)
                flowables.append(para)
                flowables.append(Spacer(1, 0.15*inch))
                current_section = []
            
            # Nouveau scénario (sous-section)
            clean_line = line.replace('**', '')
            flowables.append(Paragraph(clean_line, heading3_style))
            flowables.append(Spacer(1, 0.1*inch))
            
        # Gestion des préconditions, étapes et résultats
        elif "Précondition" in line or "Precondition" in line or line.startswith("**Précondition") or line.startswith("**Precondition"):
            if current_section:
                section_text = '\n'.join(current_section)
                para = Paragraph(section_text.replace('\n', '<br/>'), normal_style)
                flowables.append(para)
                current_section = []
            
            # Nouvelle précondition
            clean_line = line.replace('**', '')
            current_section.append(clean_line)
            in_precondition = True
            in_steps = False
            in_result = False
            
        elif "Etapes" in line or "Étapes" in line or line.startswith("**Etapes") or line.startswith("**Étapes"):
            if current_section:
                section_text = '\n'.join(current_section)
                para = Paragraph(section_text.replace('\n', '<br/>'), precondition_style if in_precondition else normal_style)
                flowables.append(para)
                current_section = []
            
            # Nouvelles étapes
            clean_line = line.replace('**', '')
            current_section.append(clean_line)
            in_precondition = False
            in_steps = True
            in_result = False
            
        elif "Résultat attendu" in line or "Résultats attendus" in line or line.startswith("**Résultat"):
            if current_section:
                section_text = '\n'.join(current_section)
                para = Paragraph(section_text.replace('\n', '<br/>'), steps_style if in_steps else normal_style)
                flowables.append(para)
                current_section = []
            
            # Nouveau résultat attendu
            clean_line = line.replace('**', '')
            current_section.append(clean_line)
            in_precondition = False
            in_steps = False
            in_result = True
            
        else:
            current_section.append(line)
    
    # Traiter la dernière section
    if current_section:
        section_text = '\n'.join(current_section)
        
        # Appliquer le style approprié pour la dernière section
        if in_precondition:
            style_to_use = precondition_style
        elif in_steps:
            style_to_use = steps_style
        elif in_result:
            style_to_use = result_style
        else:
            style_to_use = normal_style
        
        para = Paragraph(section_text.replace('\n', '<br/>'), style_to_use)
        flowables.append(para)
    
    # Génération du PDF
    doc.build(flowables)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

# Fonction pour créer un DOCX à partir du texte
def create_docx(output_text, filename="cas_de_test.docx"):
    doc = docx.Document()
    
    # Ajouter un titre
    doc.add_heading("Cas de Test", 0)
    
    # Traiter les différentes sections
    lines = output_text.split('\n')
    current_section = []
    
    for line in lines:
        if line.startswith('## ') or line.startswith('**Cas ') or line.startswith('**EXIGENCE ') or (line.startswith('EXIGENCE ') and not line.startswith('EXIGENCE:')):
            # Si on a une section précédente, on la traite
            if current_section:
                paragraph = doc.add_paragraph()
                paragraph.add_run('\n'.join(current_section))
                current_section = []
            
            # Nouvelle section
            if line.startswith('## '):
                doc.add_heading(line[3:], 1)
            elif line.startswith('**EXIGENCE '):
                doc.add_heading(line.replace('**', ''), 1)
            elif line.startswith('EXIGENCE '):
                doc.add_heading(line, 1)
            else:
                doc.add_heading(line, 1)
        elif line.startswith('**Scenario ') or line.startswith('Scenario '):
            # Si on a une section précédente, on la traite
            if current_section:
                paragraph = doc.add_paragraph()
                paragraph.add_run('\n'.join(current_section))
                current_section = []
            
            # Nouveau scénario (sous-section)
            doc.add_heading(line.replace('**', ''), 2)
        else:
            current_section.append(line)
    
    # Traiter la dernière section
    if current_section:
        paragraph = doc.add_paragraph()
        paragraph.add_run('\n'.join(current_section))
    
    # Sauvegarder dans un BytesIO
    buffer = io.BytesIO()
    doc.save(buffer)
    docx_data = buffer.getvalue()
    buffer.close()
    
    return docx_data
# Fonction pour générer des cas de test via l'API Claude
# Fonction pour générer des cas de test via l'API Claude
# Fonction pour générer des cas de test via l'API Claude
def generate_test_cases(requirements, format_type, context="", example_case=""):
    import os
    from dotenv import load_dotenv
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Récupérer la clé API depuis les variables d'environnement
    api_key = get_api_key()
    
    if not api_key:
        return "Erreur: Clé API non trouvée dans les variables d'environnement. Vérifiez votre fichier .env"
    
    # Configuration pour l'API
    headers = {
        "anthropic-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": api_key
    }
    
    # Exemple de format par défaut
    exemple_format_defaut = """
**Cas fonctionnels
**Scenario (1) : Connexion OK avec des identifiants valides.
Précondition :** L'utilisateur est inscrit avec un e-Mail valide et un MP.
**Etapes :**
1. Accéder à la page de connexion.
2. Saisir l'e-Mail et le MP valides.
3. Cliquer sur "Se connecter".
**Résultat attendu** : L'utilisateur est redirigé vers la page d'accueil.

**Scenario (2) : Connexion KO avec un e-Mail valide et un MP invalide.
Précondition :** L'utilisateur est inscrit avec un e-Mail valide et un MP.
**Etapes :**
1. Accéder à la page de connexion.
2. Saisir un e-Mail valide et un MP invalide.
3. Cliquer sur "Se connecter".
**Résultat attendu** : Un message d'erreur s'affiche.

**Scenario (3) : Connexion KO avec un e-Mail invalide et un MP valide.
Précondition :** L'utilisateur est inscrit avec un e-Mail valide et un MP.**
Etapes :**
1. Accéder à la page de connexion.
2. Saisir un e-Mail invalide et un MP valide.
3. Cliquer sur "Se connecter".
**Résultat attendu** : Un message d'erreur s'affiche.

**Cas non-fonctionnels
**Scenario (4) : Connexion KO après plusieurs tentatives**
**Etapes :**
1. Accéder à la page de connexion.
2. Saisir un e-Mail et un MP erronés.
3. Cliquer sur "Se connecter".
4. Refaire les 3 actions plusieurs fois.
5. Un message d'erreur s'affiche et le compte est temporairement bloqué."""
    
    # Déterminer le format à utiliser
    if format_type == "custom" and example_case.strip():
        exemple_format = example_case
        format_instruction = "Format personnalisé"
    elif format_type == "gherkin":
        format_instruction = "Format Gherkin (Given, When, Then)"
        exemple_format = example_case if example_case.strip() else "Format Gherkin"
    else:
        format_instruction = "Format par défaut"
        exemple_format = exemple_format_defaut
    
    # Construire le prompt
    if format_type == "default":
        instruction = f"""
        Génère des cas de test pour l'exigence suivante en utilisant le format par défaut comme dans l'exemple ci-dessous.
        Chaque cas de test doit inclure des scénarios fonctionnels et non-fonctionnels, avec des préconditions, 
        des étapes numérotées et des résultats attendus.
        
        {"Contexte fonctionnel: " + context if context else ""}
        
        Voici un exemple du format attendu :
        
        {exemple_format}
        
        Maintenant, génère des cas de test détaillés dans ce même format pour l'exigence suivante :
        
        {requirements}
        """
    elif format_type == "gherkin":
        instruction = f"""
        Génère des cas de test pour l'exigence suivante en utilisant le format Gherkin (Given, When, Then).
        Chaque cas de test doit inclure des scénarios fonctionnels et non-fonctionnels.
        
        {"Contexte fonctionnel: " + context if context else ""}
        
        {"Exemple de format attendu: " + example_case if example_case else ""}
        
        Exigence: {requirements}
        """
    else:  # format_type == "custom"
        instruction = f"""
        Génère des cas de test pour l'exigence suivante en utilisant exactement le format personnalisé fourni en exemple.
        Respecte strictement la structure et le style de l'exemple fourni.
        
        {"Contexte fonctionnel: " + context if context else ""}
        
        Voici un exemple du format attendu :
        
        {exemple_format}
        
        Maintenant, génère des cas de test détaillés dans ce même format personnalisé pour l'exigence suivante :
        
        {requirements}
        """
        
    system_prompt = """Tu es un expert en tests logiciels qui génère des cas de test de haute qualité.
    Ton travail consiste à analyser des exigences et à produire des scénarios de test complets, exhaustifs et précis.
    Pour chaque exigence, couvre tous les aspects fonctionnels et non-fonctionnels (performance, sécurité, accessibilité, etc.)."""
    
    # Appel direct à l'API Claude via requests
    import requests
    import time
    
    # Logique de retry avec backoff exponentiel
    max_retries = 3
    retry_delay = 2  # secondes
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 8000,
                    "temperature": 0.2,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user", 
                            "content": instruction
                        }
                    ]
                }
            )
            
            if response.status_code == 200:
                try:
                    content = response.json().get("content", [])
                    text_content = ""
                    for item in content:
                        if item.get("type") == "text":
                            text_content += item.get("text", "")
                    return text_content if text_content else "Pas de texte dans la réponse"
                except Exception as e:
                    return f"Erreur lors du traitement de la réponse: {str(e)}"
            # Si API surchargée, attendre et réessayer
            elif response.status_code == 529:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)
                    time.sleep(wait_time)
                    continue
                else:
                    return f"L'API est actuellement surchargée. Veuillez réessayer plus tard."
            else:
                return f"Erreur de l'API: {response.status_code} - {response.text}"
        
        except Exception as e:
            return f"Erreur lors de l'appel à l'API Claude: {str(e)}"

# Fonction pour le chatbot qui corrige/modifie les résultats
def chat_with_results(user_query, test_cases, conversation_history):
    import os
    from dotenv import load_dotenv
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Récupérer la clé API depuis les variables d'environnement
    api_key = get_api_key()
    
    if not api_key:
        return "Erreur: Clé API non trouvée dans les variables d'environnement. Vérifiez votre fichier .env"
    
    # Configuration pour l'API
    headers = {
        "anthropic-api-key": api_key,
        "content-type": "application/json",
        "anthropic-version": "2023-06-01",
        "x-api-key": api_key
    }
    
    
    # Construire l'historique des messages pour l'API
    messages = []
    
    # Ajouter l'historique de conversation existant
    for entry in conversation_history:
        messages.append({
            "role": entry["role"],
            "content": entry["content"]
        })
    
    # Ajouter le message actuel de l'utilisateur
    messages.append({
        "role": "user",
        "content": user_query
    })
    
    system_prompt = f"""Tu es un assistant spécialisé dans la correction et l'amélioration des cas de test.
    Ton travail consiste à aider l'utilisateur à améliorer, corriger ou modifier les cas de test qui ont été générés.
    
    Voici les cas de test actuels sur lesquels tu dois travailler :
    
    {test_cases}
    
    RÈGLES ABSOLUES À SUIVRE:
    1. CONSERVE TOUJOURS TOUS LES SCÉNARIOS ORIGINAUX dans ta réponse, même quand tu ajoutes ou modifies un seul scénario.
    2. JAMAIS fournir uniquement les scénarios ajoutés ou modifiés - tu dois toujours fournir le document COMPLET.
    3. Quand l'utilisateur demande de "changer le scénario X", tu modifies ce scénario tout en conservant tous les autres scénarios.
    4. Quand l'utilisateur demande d'"ajouter des scénarios", tu ajoutes les nouveaux scénarios APRÈS tous les scénarios existants.
    5. Si tu modifies ET ajoutes des scénarios, assure-toi que TOUS les scénarios (originaux modifiés + nouveaux) apparaissent dans ta réponse.
    6. La numérotation des scénarios doit rester cohérente (Scenario 1, Scenario 2, etc.).
    
    FORMAT DE RÉPONSE REQUIS:
    - Au début de ta réponse, ajoute exactement: MODIFIED:START
    - Ensuite, inclus TOUS les cas de test (originaux + modifiés + nouveaux)
    - À la fin des cas de test, ajoute exactement: MODIFIED:END
    - Après ces balises, explique brièvement les modifications effectuées
    
    EXEMPLES:
    Si les cas de test originaux contiennent les scénarios 1, 2, 3 et qu'on te demande de changer le scénario 1,
    ta réponse doit contenir les scénarios 1 (modifié), 2 et 3 (inchangés).
    
    Si on te demande d'ajouter des scénarios, ta réponse doit contenir les scénarios 1, 2, 3 (inchangés) suivis des nouveaux scénarios 4, 5, etc.
    
    Si on te demande de changer le scénario 2 ET d'ajouter de nouveaux scénarios, ta réponse doit contenir les scénarios 1 (inchangé), 
    2 (modifié), 3 (inchangé), suivis des nouveaux scénarios 4, 5, etc.
    
    Sois toujours poli et professionnel dans tes explications."""
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 8000,
                "temperature": 0.3,
                "system": system_prompt,
                "messages": messages
            }
        )
        
        if response.status_code == 200:
            try:
                content = response.json().get("content", [])
                text_content = ""
                for item in content:
                    if item.get("type") == "text":
                        text_content += item.get("text", "")
                
                # Extraction des cas de test modifiés si présents
                if "MODIFIED:START" in text_content and "MODIFIED:END" in text_content:
                    start_index = text_content.find("MODIFIED:START") + len("MODIFIED:START")
                    end_index = text_content.find("MODIFIED:END")
                    if start_index > 0 and end_index > start_index:
                        st.session_state.modified_test_cases = text_content[start_index:end_index].strip()
                
                # Nettoyer le texte pour l'affichage
                display_text = text_content.replace("MODIFIED:START", "").replace("MODIFIED:END", "")
                return display_text if display_text else "Pas de texte dans la réponse"
            except Exception as e:
                return f"Erreur lors du traitement de la réponse: {str(e)}"
        else:
            return f"Erreur de l'API: {response.status_code} - {response.text}"
        
    except Exception as e:
        return f"Erreur lors de l'appel à l'API Claude: {str(e)}"


# Fonction pour le chatbot qui corrige/modifie les résultats

    # Titre de l'application
st.title("Assistant IA - Générateur des Cas de test")
st.markdown("---")

# Initialiser les variables de session
if 'test_cases' not in st.session_state:
    st.session_state.test_cases = ""
    
if 'requirements' not in st.session_state:
    st.session_state.requirements = ""
    
if 'format_type' not in st.session_state:
    st.session_state.format_type = "default"
    
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
    
if 'modified_test_cases' not in st.session_state:
    st.session_state.modified_test_cases = ""

if 'chat_count' not in st.session_state:
    st.session_state.chat_count = 0

# NOUVELLE STRUCTURE DE L'APPLICATION - 2 colonnes
col_input, col_output = st.columns([1, 1], gap="large")

# COLONNE 1 - Entrées utilisateur
with col_input:
    st.subheader("📝 Paramètres")
    
    # Section Contexte
    with st.expander("Contexte Fonctionnel", expanded=True):
        context_tab1, context_tab2 = st.tabs(["Saisie manuelle", "Upload de fichier"])
        
        with context_tab1:
            context_input = st.text_area("Description générale de l'application", 
                               help="Contextualisez les cas de test", 
                               height=100)
        
        with context_tab2:
            context_file = st.file_uploader("Choisir un fichier de contexte", type=["txt", "docx", "pdf"], key="context_file")
            if context_file is not None:
                try:
                    if context_file.name.endswith('.docx'):
                        context_input = extract_text_from_docx(context_file)
                    elif context_file.name.endswith('.pdf'):
                        context_file.seek(0)
                        context_input = extract_text_from_pdf(context_file)
                    else:
                        context_file.seek(0)
                        context_input = context_file.getvalue().decode("utf-8")
                    
                    st.success(f"Contexte chargé depuis '{context_file.name}'")
                except Exception as e:
                    st.error(f"Erreur lors du chargement: {str(e)}")
    
    # Section Exigence
    with st.expander("Exigence", expanded=True):
        req_tab1, req_tab2 = st.tabs(["Saisie manuelle", ""])
        
        with req_tab1:
            requirements_input = st.text_area("Saisissez votre exigence", height=150)
            if requirements_input:
                st.session_state.requirements = requirements_input
        
        
    
    # Section Format
    with st.expander("Format des Cas de Test", expanded=True):
        format_option = st.radio(
            "Choisissez le format",
            ("Par Défaut", "Gherkin (Given When Then)", "Personnalisé (basé sur l'exemple)"),
            captions=["Format standard des cas de test", "Format Gherkin", "Format basé sur l'exemple fourni"]
        )
        
        if format_option == "Par Défaut":
            st.session_state.format_type = "default"
        elif format_option == "Gherkin (Given When Then)":
            st.session_state.format_type = "gherkin"
        else:
            st.session_state.format_type = "custom"
        
        example_case = st.text_area(
            "Exemple d'un cas de test" + (" (obligatoire)" if format_option == "Personnalisé (basé sur l'exemple)" else " (optionnel)"),
            height=150
        )
    
    # Bouton de génération
    generate_btn = st.button("Générer les Cas de Test", use_container_width=True)
    
    # Style CSS personnalisé pour cette colonne
    st.markdown("""
    <style>
        div[data-testid="stExpander"] {
            background-color: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 15px;
            padding: 5px;
        }
    </style>
    """, unsafe_allow_html=True)
    # COLONNE 2 - Résultats et interactions
with col_output:
    st.subheader("📋 Résultats")
    
    # Zone d'affichage des résultats
    result_container = st.container(height=400, border=True)
    
    # Afficher le contenu modifié en priorité s'il existe, sinon afficher les résultats originaux
    with result_container:
        if st.session_state.modified_test_cases:
            st.markdown(st.session_state.modified_test_cases)
        elif st.session_state.test_cases:
            st.markdown(st.session_state.test_cases)
        else:
            st.info("Les cas de test générés apparaîtront ici.")
    
    # Boutons d'exportation
    if st.session_state.modified_test_cases or st.session_state.test_cases:
        col_pdf, col_docx = st.columns(2)
        
        with col_pdf:
            # Utiliser le contenu modifié s'il existe, sinon utiliser les résultats originaux
            content_to_export = st.session_state.modified_test_cases if st.session_state.modified_test_cases else st.session_state.test_cases
            pdf_data = create_pdf(content_to_export)
            pdf_html = create_download_link(pdf_data, "pdf", "cas_de_test.pdf")
            st.markdown(pdf_html, unsafe_allow_html=True)
        
        with col_docx:
            content_to_export = st.session_state.modified_test_cases if st.session_state.modified_test_cases else st.session_state.test_cases
            docx_data = create_docx(content_to_export)
            docx_html = create_download_link(docx_data, "docx", "cas_de_test.docx")
            st.markdown(docx_html, unsafe_allow_html=True)
    
    # Chatbot pour les modifications (limité à 5 échanges)
    if st.session_state.test_cases:
        st.markdown("---")
        st.subheader("💬 Assistant de Correction (limité à 5 échanges)")
        
        # Afficher le compteur d'échanges restants
        remaining_exchanges = 5 - st.session_state.chat_count
        st.info(f"Échanges restants: {remaining_exchanges}/5")
        
        if st.session_state.chat_count >= 5:
            st.warning("Vous avez atteint la limite de 5 échanges. Vous ne pouvez plus faire de modifications.")
            
            # Afficher l'historique des messages
            with st.expander("Voir l'historique des conversations", expanded=False):
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.markdown(f"**Vous:** {message['content']}")
                        st.markdown("---")
                    else:
                        st.markdown(f"**Assistant:** {message['content'].replace('MODIFIED:START', '').replace('MODIFIED:END', '')}")
                        st.markdown("---")
        else:
            # Zone de saisie du chat
            user_message = st.text_area("Demandez des modifications ou des améliorations:", 
                                         placeholder="Exemple: Ajouter un scénario de test pour...", 
                                         height=100,
                                         key="user_message")
            
            # Bouton pour envoyer le message
            chat_btn = st.button("Envoyer la demande", use_container_width=True)
            
            # Traitement de l'envoi du message
            if chat_btn and user_message:
                # Compteur d'échanges
                st.session_state.chat_count += 1
                
                # Ajouter le message de l'utilisateur à l'historique
                st.session_state.chat_history.append({
                    "role": "user",
                    "content": user_message
                })
                
                # Obtenir la réponse du chatbot
                content_to_modify = st.session_state.modified_test_cases if st.session_state.modified_test_cases else st.session_state.test_cases
                with st.spinner("L'assistant réfléchit..."):
                    response = chat_with_results(
                        user_message, 
                        content_to_modify,
                        st.session_state.chat_history
                    )
                    
                    # Ajouter la réponse à l'historique (sans les marqueurs)
                    clean_response = response.replace('MODIFIED:START', '').replace('MODIFIED:END', '')
                    st.session_state.chat_history.append({
                        "role": "assistant",
                        "content": clean_response
                    })
                
                # Recharger la page pour afficher les résultats mis à jour
                st.rerun()
            
            
    # Traitement du bouton de génération
if generate_btn:
    if not st.session_state.requirements:
        st.error("Veuillez saisir une exigence ou uploader un fichier.")
    elif st.session_state.format_type == "custom" and not example_case.strip():
        st.error("Pour utiliser le format personnalisé, vous devez fournir un exemple de cas de test.")
    else:
        with st.spinner("Génération des cas de test en cours..."):
            try:
                # Réinitialiser l'état lors d'une nouvelle génération
                st.session_state.modified_test_cases = ""
                st.session_state.chat_history = []
                st.session_state.chat_count = 0
                
                # Générer les cas de test
                st.session_state.test_cases = generate_test_cases(
                    st.session_state.requirements,
                    st.session_state.format_type,
                    context_input,
                    example_case
                )
                
                # Recharger la page pour afficher les résultats
                st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la génération: {str(e)}")

# Ajouter du CSS personnalisé
st.markdown("""
<style>
    .stButton button {
        background-color: #0066cc;
        color: white;
        font-weight: bold;
    }
    .stButton button:hover {
        background-color: #004d99;
    }
    .css-1aumxhk {
        background-color: #f8f9fa;
    }
    .stTextArea label {
        font-weight: bold;
    }
    .stRadio label {
        font-weight: bold;
    }
    
    /* Styles améliorés pour l'interface en 2 colonnes */
    [data-testid="column"] {
        background-color: #ffffff;
        padding: 10px;
        border-radius: 10px;
    }
    
    /* Style pour le conteneur de résultats */
    [data-testid="stVerticalBlock"] > div[style] > div[data-testid="stVerticalBlock"] {
        background-color: #ffffff;
        border-radius: 5px;
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)
