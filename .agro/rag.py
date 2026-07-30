import os
import psycopg2

from sentence_transformers import SentenceTransformer

# --- Caminhos Portáteis ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(BASE_DIR, ".agro", "documentos")

# --- Conexão com o Supabase (schema isolado vetra_ai) ---
SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

# Modelo de embeddings carregado sob demanda (lazy load, evita custo no import)
_modelo_embedding = None


def _get_modelo():
    global _modelo_embedding
    if _modelo_embedding is None:
        _modelo_embedding = SentenceTransformer("all-MiniLM-L6-v2")
    return _modelo_embedding


def _conectar():
    if not SUPABASE_DB_URL:
        raise RuntimeError(
            "A variável de ambiente SUPABASE_DB_URL não está configurada."
        )
    return psycopg2.connect(SUPABASE_DB_URL)


def _vetor_para_sql(embedding):
    """Converte uma lista de floats no formato literal esperado pelo pgvector."""
    return "[" + ",".join(repr(float(x)) for x in embedding) + "]"


def contar_chunks():
    """Retorna quantos chunks existem na base de conhecimento (vetra_ai.knowledge_chunks)."""
    try:
        with _conectar() as conn:
            with conn.cursor() as cur:
                cur.execute("select count(*) from vetra_ai.knowledge_chunks;")
                return cur.fetchone()[0]
    except Exception as e:
        print(f"❌ Erro ao contar chunks no Supabase: {e}")
        return 0


def indexar_documentos():
    """Varre a pasta de documentos, quebra em parágrafos e salva no Supabase (pgvector)."""
    if not os.path.exists(DOCS_DIR):
        print(f"❌ A pasta de documentos não foi encontrada em: {DOCS_DIR}")
        return

    arquivos = [f for f in os.listdir(DOCS_DIR) if f.endswith(".txt")]

    if not arquivos:
        print("🌾 Nenhum documento .txt encontrado para indexar por enquanto.")
        return

    modelo = _get_modelo()
    print(f"🌾 Processando {len(arquivos)} arquivos para o RAG...")

    try:
        with _conectar() as conn:
            with conn.cursor() as cur:
                for nome_arquivo in arquivos:
                    caminho_completo = os.path.join(DOCS_DIR, nome_arquivo)
                    with open(caminho_completo, "r", encoding="utf-8") as f:
                        conteudo = f.read()

                    paragrafos = [p.strip() for p in conteudo.split("\n\n") if p.strip()]
                    if not paragrafos:
                        continue

                    embeddings = modelo.encode(paragrafos).tolist()

                    for i, (paragrafo, embedding) in enumerate(zip(paragrafos, embeddings)):
                        cur.execute(
                            """
                            insert into vetra_ai.knowledge_chunks
                                (fonte, chunk_index, conteudo, embedding)
                            values (%s, %s, %s, %s::vector)
                            on conflict (fonte, chunk_index)
                            do update set
                                conteudo = excluded.conteudo,
                                embedding = excluded.embedding;
                            """,
                            (nome_arquivo, i, paragrafo, _vetor_para_sql(embedding)),
                        )
                    print(f"✅ {nome_arquivo} indexado com sucesso ({len(paragrafos)} chunks).")
            conn.commit()
    except Exception as e:
        print(f"❌ Erro ao indexar documentos no Supabase: {e}")


def buscar_contexto(pergunta, max_resultados=2):
    """Busca os trechos mais relevantes no Supabase baseados na pergunta do usuário."""
    try:
        if contar_chunks() == 0:
            return ""

        modelo = _get_modelo()
        query_embedding = modelo.encode([pergunta])[0].tolist()
        vetor_sql = _vetor_para_sql(query_embedding)

        with _conectar() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "select fonte, conteudo, distancia "
                    "from vetra_ai.buscar_similares(%s::vector, %s);",
                    (vetor_sql, max_resultados),
                )
                resultados = cur.fetchall()

        if not resultados:
            return ""

        contexto_formatado = "\n## DOCUMENTOS DE SUPORTE (RAG):\n"
        for fonte, conteudo, _distancia in resultados:
            contexto_formatado += f"From [{fonte}]: {conteudo}\n\n"
        return contexto_formatado

    except Exception as e:
        print(f"❌ Erro ao buscar contexto no Supabase: {e}")
        return ""


if __name__ == "__main__":
    print("🚀 Iniciando indexador do RAG Vetra AI (Supabase/pgvector)...")
    indexar_documentos()
    print("📊 Total de registros no banco de vetores:", contar_chunks())
