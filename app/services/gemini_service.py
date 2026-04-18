from google import genai
from app.config import GEMINI_API_KEY


class GeminiServiceError(RuntimeError):
    pass


_client = None


def _get_client():
    global _client

    if _client is not None:
        return _client

    if not GEMINI_API_KEY:
        raise GeminiServiceError("GEMINI_API_KEY no esta configurada")

    try:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        raise GeminiServiceError(f"No se pudo inicializar Gemini: {exc}") from exc

    return _client


def _generate(prompt: str) -> str:
    client = _get_client()

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
    except Exception as exc:
        raise GeminiServiceError(f"Error al consultar Gemini: {exc}") from exc

    text = getattr(response, "text", None)
    if text:
        return text

    raise GeminiServiceError("Gemini no devolvio contenido de texto")


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

    return _generate(prompt)


def answer_question(question, summary_data):
    prompt = f"""
Responde la pregunta usando solo la información dada.

Pregunta:
{question}

Datos:
{summary_data}
"""

    return _generate(prompt)