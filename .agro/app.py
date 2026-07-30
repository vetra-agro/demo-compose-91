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
# A paleta e as cores de todos os componentes nativos (header,
# botões, chat input, sidebar) vêm do .streamlit/config.toml.
# Aqui só ajustamos tipografia e os elementos que eu mesmo desenho
# (cabeçalho e cards) — sem sobrescrever CSS interno do Streamlit.
# ============================================================
strl.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Zilla+Slab:wght@600;700&display=swap');

    h1, h2, h3 { font-family: 'Zilla Slab', serif !important; }

    .agrovy-header { padding-bottom: 1rem; border-bottom: 2px solid #D9A441; margin-bottom: 1.5rem; }
    .agrovy-header h1 { color: #D9A441; font-size: 2rem; margin: 0; }
    .agrovy-header p { opacity: 0.7; margin: 0.25rem 0 0 0; font-size: 0.95rem; }

    .agrovy-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
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
    strl.caption("Comece perguntando algo, ou escolha um ponto de partida:")
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
