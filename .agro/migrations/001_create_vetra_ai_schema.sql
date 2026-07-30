-- ============================================================
-- Vetra AI - Schema isolado para RAG (pgvector)
-- Roda no Supabase de PRODUÇÃO, mas totalmente separado
-- do schema public/ERP (sem tocar em tabelas do Vetra ERP).
-- ============================================================

-- 1. Garante que a extensão pgvector está disponível
--    (segue o mesmo padrão já usado pra PostGIS: extensão fica em "extensions")
create extension if not exists vector with schema extensions;

-- 2. Cria o schema isolado para a IA
create schema if not exists vetra_ai;

-- 3. Tabela de chunks de conhecimento (substitui o ChromaDB local)
create table if not exists vetra_ai.knowledge_chunks (
    id           bigint generated always as identity primary key,
    fonte        text not null,              -- nome do arquivo original
    chunk_index  int not null,               -- posição do chunk no documento
    conteudo     text not null,              -- texto do parágrafo/chunk
    embedding    extensions.vector(384) not null,  -- all-MiniLM-L6-v2 = 384 dimensões
    criado_em    timestamptz not null default now(),
    unique (fonte, chunk_index)
);

-- 4. Índice de busca por similaridade (cosine distance)
create index if not exists idx_knowledge_chunks_embedding
    on vetra_ai.knowledge_chunks
    using hnsw (embedding extensions.vector_cosine_ops);

-- 5. Função de busca semântica (top-N mais próximos)
create or replace function vetra_ai.buscar_similares(
    query_embedding extensions.vector(384),
    max_resultados int default 2
)
returns table (
    fonte text,
    conteudo text,
    distancia float
)
language sql
stable
as $$
    select
        fonte,
        conteudo,
        embedding <=> query_embedding as distancia
    from vetra_ai.knowledge_chunks
    order by embedding <=> query_embedding
    limit max_resultados;
$$;
