import os
import re
import requests

from rag import buscar_contexto

# --- Carrega o system prompt a partir do arquivo de contexto ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_FILE = os.path.join(BASE_DIR, "contexto", "system_prompt.txt")


def _carregar_system_prompt():
    """Extrai o texto do template salvo em contexto/system_prompt.txt."""
    try:
        with open(PROMPT_FILE, "r", encoding="utf-8") as f:
            conteudo = f.read()
        # O arquivo guarda o texto como SYSTEM_PROMPT_TEMPLATE = """...""" 
        match = re.search(r'"""(.*)"""', conteudo, re.DOTALL)
        if match:
            return match.group(1).strip()
        return conteudo.strip()
    except FileNotFoundError:
        return "Você é a VETRA IA, assistente da Vetra Agro. Responda sempre em português."


SYSTEM_PROMPT = _carregar_system_prompt()

# --- Configuração da API (Google Gemini - camada gratuita) ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


def perguntar_vetra(pergunta: str) -> str:
    """Monta o prompt (system + RAG + pergunta) e consulta a API Gemini."""
    if not GEMINI_API_KEY:
        return (
            "⚠️ A chave GEMINI_API_KEY não está configurada. "
            "Defina essa variável de ambiente para ativar o agente."
        )

    contexto_rag = buscar_contexto(pergunta)

    prompt_completo = f"{SYSTEM_PROMPT}\n\n{contexto_rag}\n\nPergunta: {pergunta}"

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt_completo}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        },
    }

    headers = {"Content-Type": "application/json"}
    params = {"key": GEMINI_API_KEY}

    try:
        resposta = requests.post(
            GEMINI_URL, headers=headers, params=params, json=payload, timeout=30
        )
        resposta.raise_for_status()
        dados = resposta.json()

        candidatos = dados.get("candidates", [])
        if not candidatos:
            return "🌾 Não consegui gerar uma resposta agora. Tente novamente."

        partes = candidatos[0].get("content", {}).get("parts", [])
        texto_resposta = "".join(p.get("text", "") for p in partes).strip()

        return texto_resposta or "🌾 Não sei responder isso com certeza no momento."

    except requests.exceptions.HTTPError as e:
        return f"❌ Erro na API Gemini ({resposta.status_code}): {e}"
    except requests.exceptions.RequestException as e:
        return f"❌ Erro de conexão com a API Gemini: {e}"


if __name__ == "__main__":
    print("🚀 Testando o agente Vetra AI...")
    print(perguntar_vetra("Quem é você?"))
