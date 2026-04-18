from google import genai
from app.config import GEMINI_API_KEY

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY no está configurada")

client = genai.Client(api_key=GEMINI_API_KEY)


def generate_report(summary_data):
    prompt = f"""
Eres un analista ambiental.

Analiza los datos de calidad del agua y genera:
1. Resumen ejecutivo
2. Hallazgos clave
3. Riesgos o anomalías
4. Recomendaciones

No inventes datos. Usa español.

Datos:
{summary_data}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text


def answer_question(question, summary_data):
    prompt = f"""
Responde la pregunta usando solo la información dada.

Pregunta:
{question}

Datos:
{summary_data}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    return response.text