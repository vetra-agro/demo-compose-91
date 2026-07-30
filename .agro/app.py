import os
import streamlit as strl

# Ponte: no Streamlit Community Cloud os secrets vivem em st.secrets, não em
# variáveis de ambiente. Copiamos para os.environ ANTES de importar agent/rag,
# já que esses módulos leem GEMINI_API_KEY, SUPABASE_DB_URL e GEMINI_MODEL na importação.
for _chave in ("GEMINI_API_KEY", "SUPABASE_DB_URL", "GEMINI_MODEL"):
    if _chave in strl.secrets and not os.environ.get(_chave):
        os.environ[_chave] = strl.secrets[_chave]

# Importa o motor do agente e do RAG que foi criado
from agent import perguntar_vetra
from rag import indexar_documentos, contar_chunks

# Configurações de página portáteis
strl.set_page_config(page_title="Agrovy — DataAhead", page_icon="🌱", layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, ".agro", "documentos")

PERGUNTAS_SUGERIDAS = [
    "Quais certificações preciso pra exportar soja?",
    "Como estruturar o cadastro de talhões?",
    "Resuma os documentos que já indexei",
]

# ============================================================
# IDENTIDADE VISUAL — Agrovy (v2)
# Fundo quase-preto + um único destaque dourado forte.
# Cobre explicitamente header/toolbar/chat-input do Streamlit,
# não só os elementos de conteúdo.
# ============================================================
strl.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@600;700&family=Inter:wght@400;500;600&display=swap');

    :root {
        --bg: #12140E;
        --surface: #1B1E15;
        --surface-2: #23271A;
        --border: #34381F;
        --accent: #E4B655;
        --text: #F3EFE4;
        --text-muted: #9C9884;
    }

    html, body, .stApp {
        background-color: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }

    h1, h2, h3 { font-family: 'Zilla Slab', serif !important; color: var(--text) !important; }

    /* --- Barra superior padrão do Streamlit --- */
    [data-testid="stHeader"] {
        background-color: var(--bg) !important;
    }
    [data-testid="stToolbar"] button, [data-testid="stHeader"] svg {
        color: var(--text) !important;
    }

    /* --- Cabeçalho Agrovy --- */
    .agrovy-header { padding: 0 0 1rem 0; border-bottom: 2px solid var(--accent); margin-bottom: 1.5rem; }
    .agrovy-header h1 { color: var(--accent) !important; font-size: 2rem; margin: 0; }
    .agrovy-header p { color: var(--text-muted); margin: 0.25rem 0 0 0; font-size: 0.95rem; }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] { background-color: var(--surface) !important; border-right: 1px solid var(--border); }
    [data-testid="stSidebar"] h1 { color: var(--accent) !important; font-size: 1.2rem; }
    [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
        color: var(--text) !important;
    }

    .agrovy-card {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    [data-testid="stMetricValue"] { color: var(--accent) !important; }
    [data-testid="stMetricLabel"] { color: var(--text-muted) !important; }

    /* --- Mensagens de chat --- */
    [data-testid="stChatMessage"] {
        background: var(--surface) !important;
        border: 1px solid var(--border);
        border-radius: 12px;
    }
    [data-testid="stChatMessage"] p { color: var(--text) !important; }

    /* --- Botões --- */
    .stButton button {
        background: var(--surface-2) !important;
        color: var(--text) !important;
        border: 1px solid var(--border) !important;
        border-radius: 8px !important;
        font-weight: 500;
    }
    .stButton button:hover {
        background: var(--accent) !important;
        color: var(--bg) !important;
        border-color: var(--accent) !important;
    }

    /* --- Caixa de chat (container inteiro, não só o textarea) --- */
    [data-testid="stBottomBlockContainer"],
    [data-testid="stChatInputContainer"],
    .stChatFloatingInputContainer {
        background-color: var(--bg) !important;
    }
    [data-testid="stChatInput"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
    }
    [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: var(--text) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- BARRA LATERAL: Painel de Campo ---
with strl.sidebar:
    strl.title("🌱 Painel de Campo")

    strl.markdown('<div class="agrovy-card">', unsafe_allow_html=True)
    strl.subheader("Base de conhecimento")
    try:
        total_vetores = contar_chunks()
    except Exception:
        total_vetores = 0
    strl.metric(label="Chunks indexados", value=total_vetores)
    strl.markdown('</div>', unsafe_allow_html=True)

    strl.markdown('<div class="agrovy-card">', unsafe_allow_html=True)
    strl.subheader("Certificações e diretrizes")
    strl.caption("Envie um .txt para a Agrovy consultar nas respostas.")
    arquivo_enviado = strl.file_uploader("Arquivo .txt", type=["txt"], label_visibility="collapsed")

    if arquivo_enviado is not None:
        caminho_salvar = os.path.join(DOCS_DIR, arquivo_enviado.name)
        with open(caminho_salvar, "wb") as f:
            f.write(arquivo_enviado.getbuffer())

        with strl.spinner("Indexando documento na base vetorial..."):
            indexar_documentos()
        strl.success(f"'{arquivo_enviado.name}' indexado.")
    strl.markdown('</div>', unsafe_allow_html=True)

    strl.caption("DataAhead · Assistente Agrovy")

# --- CABEÇALHO ---
strl.markdown(
    """
    <div class="agrovy-header">
        <h1>🌱 Agrovy</h1>
        <p>Assistente de inteligência da DataAhead para negócios, certificações e dados de safra</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Inicializa o histórico de mensagens na sessão do Streamlit se não existir
if "messages" not in strl.session_state:
    strl.session_state.messages = []

pergunta_disparada = None

# Estado vazio: convite à ação em vez de tela em branco
if not strl.session_state.messages:
    strl.markdown(
        "<p style='color: var(--text-muted);'>Comece perguntando algo, ou escolha um ponto de partida:</p>",
        unsafe_allow_html=True,
    )
    colunas = strl.columns(len(PERGUNTAS_SUGERIDAS))
    for coluna, sugestao in zip(colunas, PERGUNTAS_SUGERIDAS):
        with coluna:
            if strl.button(sugestao, use_container_width=True):
                pergunta_disparada = sugestao

# Renderiza as mensagens anteriores do histórico na tela
for message in strl.session_state.messages:
    avatar = "🌱" if message["role"] == "assistant" else "🧑‍🌾"
    with strl.chat_message(message["role"], avatar=avatar):
        strl.markdown(message["content"])

# Campo de entrada de texto para a conversa (Chat Input)
prompt = strl.chat_input("Pergunte à Agrovy sobre safras, certificações ou dados...")
prompt = prompt or pergunta_disparada

if prompt:
    with strl.chat_message("user", avatar="🧑‍🌾"):
        strl.markdown(prompt)
    strl.session_state.messages.append({"role": "user", "content": prompt})

    with strl.chat_message("assistant", avatar="🌱"):
        placeholder_resposta = strl.empty()
        placeholder_resposta.markdown("_Consultando a base de conhecimento..._")

        resposta_final = perguntar_vetra(prompt)

        placeholder_resposta.markdown(resposta_final)

    strl.session_state.messages.append({"role": "assistant", "content": resposta_final})
