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
strl.set_page_config(page_title="Agrovy by DataAhead", page_icon="🌱", layout="wide")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, ".agro", "documentos")

PERGUNTAS_SUGERIDAS = [
    "Quais certificações preciso pra exportar soja?",
    "Como estruturar o cadastro de talhões?",
    "Resuma os documentos que já indexei",
]

# ============================================================
# IDENTIDADE VISUAL — Agrovy
# Paleta: terra ao entardecer (não o clichê cream/terracota de IA)
# ============================================================
strl.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@500;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap');

    :root {
        --solo-fundo: #1C1F16;
        --solo-superficie: #262B1D;
        --solo-superficie-alta: #2F3524;
        --ocre: #A9722E;
        --trigo: #D4A94A;
        --musgo: #6B8F47;
        --texto: #EDE8DD;
        --texto-suave: #A9A38C;
        --borda: #3A3F2C;
    }

    .stApp {
        background:
            repeating-linear-gradient(
                115deg,
                rgba(212, 169, 74, 0.035) 0px,
                rgba(212, 169, 74, 0.035) 2px,
                transparent 2px,
                transparent 46px
            ),
            var(--solo-fundo);
        color: var(--texto);
        font-family: 'Inter', sans-serif;
    }

    h1, h2, h3 { font-family: 'Zilla Slab', serif !important; letter-spacing: 0.01em; }

    /* Cabeçalho Agrovy */
    .agrovy-header { padding: 0.4rem 0 1.2rem 0; border-bottom: 1px solid var(--borda); margin-bottom: 1.4rem; }
    .agrovy-header h1 { color: var(--trigo); font-size: 2.1rem; margin: 0; }
    .agrovy-header p { color: var(--texto-suave); margin: 0.2rem 0 0 0; font-size: 0.95rem; }

    /* Sidebar como "Painel de Campo" */
    [data-testid="stSidebar"] { background-color: var(--solo-superficie); border-right: 1px solid var(--borda); }
    [data-testid="stSidebar"] h1 { color: var(--trigo); font-size: 1.3rem; }
    [data-testid="stSidebar"] h3 { color: var(--texto); font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.06em; }

    .agrovy-card {
        background: var(--solo-superficie-alta);
        border: 1px solid var(--borda);
        border-radius: 4px 14px 4px 14px;
        padding: 0.9rem 1rem;
        margin-bottom: 0.9rem;
    }

    /* Métricas com fonte de "telemetria" */
    [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace; color: var(--trigo); }
    [data-testid="stMetricLabel"] { color: var(--texto-suave); }

    /* Bolhas de chat — cantos cortados, como parcela de terra, não bolha genérica */
    [data-testid="stChatMessage"] {
        background: var(--solo-superficie);
        border: 1px solid var(--borda);
        border-radius: 3px 16px 3px 16px;
    }

    /* Botões */
    .stButton button {
        background: var(--ocre);
        color: var(--texto);
        border: none;
        border-radius: 3px 12px 3px 12px;
        font-weight: 500;
    }
    .stButton button:hover { background: var(--trigo); color: var(--solo-fundo); }

    /* Campo de chat */
    [data-testid="stChatInput"] textarea { background: var(--solo-superficie) !important; color: var(--texto) !important; }
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
        "<p style='color: var(--texto-suave);'>Comece perguntando algo, ou escolha um ponto de partida:</p>",
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
