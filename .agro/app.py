import os
import streamlit as strl

# Ponte: no Streamlit Community Cloud os secrets vivem em st.secrets, não em
# variáveis de ambiente. Copiamos para os.environ ANTES de importar agent/rag,
# já que esses módulos leem GEMINI_API_KEY e SUPABASE_DB_URL na importação.
for _chave in ("GEMINI_API_KEY", "SUPABASE_DB_URL", "GEMINI_MODEL"):
    if _chave in strl.secrets and not os.environ.get(_chave):
        os.environ[_chave] = strl.secrets[_chave]

# Importa o motor do agente e do RAG que foi criado
from agent import perguntar_vetra
from rag import indexar_documentos, contar_chunks

# Configurações de página portáteis
strl.set_page_config(page_title="Vetra AI - Agro", page_icon="🌾", layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, ".agro", "documentos")
LOG_FILE = os.path.join(BASE_DIR, ".agro", "logs", "agro_session.log")

# --- BARRA LATERAL (Gestão de Negócios e Monitoramento) ---
with strl.sidebar:
    strl.title("🚜 Painel de Controle")
    strl.markdown("---")
    
    # 1. Upload de Documentos para o RAG (Foco: Julio e Sergio)
    strl.subheader("📁 Upload de Certificações / Diretrizes")
    arquivo_enviado = strl.file_uploader("Arraste arquivos .txt aqui", type=["txt"])
    
    if arquivo_enviado is not None:
        caminho_salvar = os.path.join(DOCS_DIR, arquivo_enviado.name)
        # Salva o arquivo localmente na pasta portátil
        with open(caminho_salvar, "wb") as f:
            f.write(arquivo_enviado.getbuffer())
        
        # Roda o indexador do RAG para atualizar o ChromaDB em tempo real
        with strl.spinner("Indexando novo documento no banco de vetores..."):
            indexar_documentos()
        strl.success(f"✅ '{arquivo_enviado.name}' integrado ao RAG!")

    strl.markdown("---")
    
    # 2. Monitoramento de Contexto (Foco: Almeida e Kudo)
    strl.subheader("🕵️ Status do Tracker de Contexto (WSL2)")
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            linhas_log = f.readlines()[-6:] # Vai pega as últimas 6 linhas de processos
            logs_formatados = "".join(linhas_log)
            strl.code(logs_formatados, language="text")
    else:
        strl.info("Aguardando inicialização do Watchdog...")

    strl.markdown("---")
    # Contador de registros salvos no banco de dados semântico
    try:
        total_vetores = contar_chunks()
        strl.metric(label="Base de Conhecimento (Chunks)", value=total_vetores)
    except Exception:
        strl.metric(label="Base de Conhecimento (Chunks)", value=0)

# --- ÁREA PRINCIPAL (Interface do Chat - ChatGPT Style 😊) ---
strl.title("🌾 VETRA AI")
strl.markdown("### *Assistente Inteligente de Negócios e Engenharia Vetra Agro*")

# Inicializa o histórico de mensagens na sessão do Streamlit se não existir
if "messages" not in strl.session_state:
    strl.session_state.messages = []

# Renderiza as mensagens anteriores do histórico na tela
for message in strl.session_state.messages:
    with strl.chat_message(message["role"]):
        strl.markdown(message["content"])

# Campo de entrada de texto para a conversa (Chat Input)
if prompt := strl.chat_input("Como posso ajudar o time Vetra Agro hoje?"):
    # Vai exibe a mensagem do usuário no chat
    with strl.chat_message("user"):
        strl.markdown(prompt)
    # Adiciona ao histórico da sessão
    strl.session_state.messages.append({"role": "user", "content": prompt})

    # Bloco de processamento da resposta da IA
    with strl.chat_message("assistant"):
        placeholder_resposta = strl.empty()
        placeholder_resposta.markdown("*Vetra AI pensando com RAG...*")
        
        # Dispara a pergunta para o Ollama Docker (Gemma 4)
        resposta_final = perguntar_vetra(prompt)
        
        # Atualiza a interface com a resposta real gerada
        placeholder_resposta.markdown(resposta_final)
        
    # Adiciona a resposta da IA ao histórico da sessão
    strl.session_state.messages.append({"role": "assistant", "content": resposta_final})
