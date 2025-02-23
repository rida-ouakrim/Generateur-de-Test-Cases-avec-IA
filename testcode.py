import streamlit as st
import anthropic
from pymongo import MongoClient
import os
import pandas as pd
from datetime import datetime
import io
from bson import ObjectId
import PyPDF2
from io import BytesIO

# Configuration Anthropic
ANTHROPIC_API_KEY = "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"
MODEL = "claude-3-5-haiku-20241022"
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# Configuration MongoDB
mongo_uri = os.getenv('MONGO_URI', "mongodb://localhost:27017/")
mongo_client = MongoClient(mongo_uri)
db = mongo_client.testcase_db  # Nouvelle base de données

# Collections
projects_collection = db.projects  # Pour stocker les projets/chats
requirements_collection = db.requirements  # Pour stocker les cahiers des charges
testcases_collection = db.testcases  # Pour stocker les test cases générés
examples_collection = db.examples  # Pour stocker les exemples de test cases

# Configuration de la page Streamlit
st.set_page_config(page_title="Générateur de Test Cases", layout="wide")
st.title("Générateur de Test Cases avec IA")

# Initialisation des variables de session
if 'selected_project_id' not in st.session_state:
    st.session_state.selected_project_id = None

# Fonction pour créer un nouveau projet
def create_project(name, description):
    project = {
        "name": name,
        "description": description,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "status": "active"
    }
    project_id = projects_collection.insert_one(project).inserted_id
    st.session_state.selected_project_id = project_id
    return project_id

# Fonction pour mettre à jour un projet
def update_project(project_id, name, description):
    projects_collection.update_one(
        {"_id": ObjectId(project_id)},
        {
            "$set": {
                "name": name,
                "description": description,
                "updated_at": datetime.now()
            }
        }
    )

# Fonction pour supprimer un projet
def delete_project(project_id):
    # Supprimer le projet et tous les documents associés
    projects_collection.delete_one({"_id": ObjectId(project_id)})
    requirements_collection.delete_many({"project_id": ObjectId(project_id)})
    testcases_collection.delete_many({"project_id": ObjectId(project_id)})
    examples_collection.delete_many({"project_id": ObjectId(project_id)})
    st.session_state.selected_project_id = None

# Fonction pour extraire le texte d'un PDF
def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_file))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Erreur lors de l'extraction du texte du PDF: {str(e)}")
        return None

# Fonction pour lire le contenu d'un fichier
def read_file_content(file):
    try:
        if file.name.lower().endswith('.pdf'):
            return extract_text_from_pdf(file.getvalue())
        elif file.name.lower().endswith('.txt'):
            return file.getvalue().decode('utf-8')
        elif file.name.lower().endswith('.docx'):
            # Pour les fichiers DOCX, on stocke le binaire pour l'instant
            # TODO: Ajouter le support pour l'extraction de texte des fichiers DOCX
            return file.getvalue()
        else:
            return file.getvalue()
    except Exception as e:
        st.error(f"Erreur lors de la lecture du fichier {file.name}: {str(e)}")
        return None

# Fonction pour sauvegarder un fichier d'exigences
def save_requirement(file, project_id):
    if file is not None:
        file_content = file.getvalue()  # Garder le contenu binaire
        text_content = read_file_content(file)  # Extraire le texte si possible
        
        requirement_doc = {
            "project_id": ObjectId(project_id),
            "filename": file.name,
            "content": file_content,
            "text_content": text_content,  # Stocker le texte extrait
            "file_type": file.name.split('.')[-1].lower(),
            "uploaded_at": datetime.now(),
            "type": "requirement"
        }
        return requirements_collection.insert_one(requirement_doc).inserted_id

# Fonction pour sauvegarder un exemple de test case
def save_example(file, project_id):
    if file is not None:
        file_content = file.getvalue()  # Garder le contenu binaire
        text_content = read_file_content(file)  # Extraire le texte si possible
        
        example_doc = {
            "project_id": ObjectId(project_id),
            "filename": file.name,
            "content": file_content,
            "text_content": text_content,  # Stocker le texte extrait
            "file_type": file.name.split('.')[-1].lower(),
            "uploaded_at": datetime.now(),
            "type": "example"
        }
        return examples_collection.insert_one(example_doc).inserted_id

# Fonction pour sauvegarder les test cases générés
def save_testcases(project_id, content, format_type):
    testcase_doc = {
        "project_id": ObjectId(project_id),
        "content": content,
        "format": format_type,
        "generated_at": datetime.now()
    }
    return testcases_collection.insert_one(testcase_doc).inserted_id

# Fonction pour générer les test cases
def generate_test_cases(context, example_file=None, output_format="text"):
    prompt = f"""En tant qu'expert en test logiciel, générez des cas de test basés sur le contexte suivant:

Contexte:
{context}

Instructions:
- Créer des test cases détaillés et structurés
- Inclure les prérequis, les étapes de test, et les résultats attendus
- Ajouter des cas de test pour les scénarios positifs et négatifs
- Prioriser les tests selon leur importance
"""

    if example_file:
        prompt += f"\nVoici un exemple de format de test case à suivre:\n{example_file}\n"

    message = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    response = message.content[0].text
    
    if output_format == "excel":
        # Conversion en format Excel
        df = pd.DataFrame([
            line.split('|') for line in response.split('\n') if '|' in line
        ])
        output = io.BytesIO()
        df.to_excel(output, index=False)
        return output.getvalue()
    
    return response

# Interface utilisateur Streamlit
def main():
    # Sidebar pour la gestion des projets
    with st.sidebar:
        st.header("Gestion des Projets")
        
        # Création d'un nouveau projet
        with st.expander("Créer un nouveau projet"):
            new_project_name = st.text_input("Nom du projet")
            new_project_description = st.text_area("Description")
            if st.button("Créer"):
                if new_project_name:
                    create_project(new_project_name, new_project_description)
                    st.success("Projet créé avec succès!")
                    st.rerun()

        # Liste des projets existants
        st.subheader("Projets existants")
        projects = list(projects_collection.find())
        
        if not projects:
            st.info("Aucun projet n'existe. Créez votre premier projet!")
        else:
            project_names = {str(project['_id']): project['name'] for project in projects}
            selected_project_id = st.selectbox(
                "Sélectionner un projet",
                options=list(project_names.keys()),
                format_func=lambda x: project_names[x]
            )
            st.session_state.selected_project_id = selected_project_id

    # Zone principale
    if st.session_state.selected_project_id:
        selected_project = projects_collection.find_one({"_id": ObjectId(st.session_state.selected_project_id)})
        
        if selected_project:
            # Actions sur le projet sélectionné
            col1, col2 = st.columns([3, 1])
            with col1:
                st.header(selected_project["name"])
                st.write(selected_project["description"])
            
            with col2:
                if st.button("Supprimer ce projet"):
                    delete_project(st.session_state.selected_project_id)
                    st.success("Projet supprimé!")
                    st.rerun()
            
            # Formulaire de génération de test cases
            st.subheader("Générer des Test Cases")
            
            # Entrée des informations
            descriptif = st.text_area("Descriptif de la fonctionnalité", help="Décrivez la fonctionnalité à tester")
            contexte_fonctionnel = st.text_area("Contexte fonctionnel", help="Décrivez le contexte fonctionnel")
            contexte_technique = st.text_area("Contexte technique", help="Décrivez le contexte technique")
            
            # Upload de fichiers
            cahier_charges = st.file_uploader("Cahier des charges", type=["pdf", "docx", "txt"])
            example_test_case = st.file_uploader("Exemple de test case", type=["pdf", "docx", "txt"])
            
            # Format de sortie
            output_format = st.radio("Format de sortie", ["text", "excel"])
            
            if st.button("Générer les test cases"):
                with st.spinner("Génération des test cases en cours..."):
                    context = f"""
                    Descriptif: {descriptif}
                    
                    Contexte fonctionnel: {contexte_fonctionnel}
                    
                    Contexte technique: {contexte_technique}
                    """
                    
                    # Sauvegarder les fichiers
                    if cahier_charges:
                        save_requirement(cahier_charges, st.session_state.selected_project_id)
                    if example_test_case:
                        example_id = save_example(example_test_case, st.session_state.selected_project_id)
                        example_doc = examples_collection.find_one({"_id": example_id})
                        example_content = example_doc.get("text_content")
                    else:
                        example_content = None
                    
                    # Générer les test cases
                    result = generate_test_cases(context, example_content, output_format)
                    
                    # Sauvegarder les test cases générés
                    save_testcases(st.session_state.selected_project_id, result, output_format)
                    
                    if output_format == "excel":
                        st.download_button(
                            label="Télécharger les test cases (Excel)",
                            data=result,
                            file_name=f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.text_area("Test Cases générés", result, height=400)

            # Historique des test cases générés
            with st.expander("Historique des test cases"):
                testcases = testcases_collection.find({"project_id": ObjectId(st.session_state.selected_project_id)})
                for testcase in testcases:
                    st.write(f"Généré le: {testcase['generated_at']}")
                    if testcase['format'] == 'excel':
                        st.download_button(
                            label=f"Télécharger test cases du {testcase['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}",
                            data=testcase['content'],
                            file_name=f"test_cases_{testcase['generated_at'].strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.text_area(
                            f"Test cases du {testcase['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}",
                            testcase['content'],
                            height=200
                        )

if __name__ == "__main__":
    main()