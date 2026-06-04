## O que faz: cria o módulo que combina busca vetorial (semântica) com BM25 (palavras-chave) — o resultado será muito mais preciso do que cada um separado.
from rank_bm25 import BM25Okapi
from app.rag.embeddings import gerar_embedding
from app.config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# Conecta ao Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def carregar_todos_chunks() -> list[dict]:
    """Carrega todos os chunks do Supabase."""
    resultado = supabase.table("documents").select("id, content, metadata").execute()
    return resultado.data

def buscar_bm25(pergunta: str, chunks: list[dict], limite: int = 3) -> list[dict]:
    """Busca por palavras-chave usando BM25."""
    
    # Tokeniza os chunks
    corpus = [chunk["content"].lower().split() for chunk in chunks]
    bm25 = BM25Okapi(corpus)
    
    # Tokeniza a pergunta e calcula scores
    tokens_pergunta = pergunta.lower().split()
    scores = bm25.get_scores(tokens_pergunta)
    
    # Ordena por score e retorna os melhores
    chunks_com_score = [
        {**chunks[i], "bm25_score": float(scores[i])}
        for i in range(len(chunks))
    ]
    return sorted(chunks_com_score, key=lambda x: x["bm25_score"], reverse=True)[:limite]

def buscar_vetorial(pergunta: str, limite: int = 3) -> list[dict]:
    """Busca por similaridade vetorial no Supabase."""
    embedding = gerar_embedding(pergunta)
    resultado = supabase.rpc("buscar_documentos", {
        "query_embedding": embedding,
        "match_count": limite
    }).execute()
    return [{**doc, "vector_score": doc["similarity"]} for doc in resultado.data]

def hybrid_search(pergunta: str, limite: int = 3, alpha: float = 0.5) -> list[dict]:
    """
    Combina BM25 e busca vetorial com score híbrido.
    alpha=0.5 significa peso igual para ambos.
    alpha=1.0 significa apenas vetorial.
    alpha=0.0 significa apenas BM25.
    """
    chunks = carregar_todos_chunks()
    
    # Busca vetorial e BM25
    resultados_vetor = buscar_vetorial(pergunta, limite=len(chunks))
    resultados_bm25 = buscar_bm25(pergunta, chunks, limite=len(chunks))
    
    # Normaliza scores entre 0 e 1
    max_bm25 = max((r["bm25_score"] for r in resultados_bm25), default=1)
    
    # Combina scores por id
    scores_combinados = {}
    
    for doc in resultados_vetor:
        scores_combinados[doc["id"]] = {
            "doc": doc,
            "vector_score": doc["vector_score"],
            "bm25_score": 0.0
        }
    
    for doc in resultados_bm25:
        bm25_normalizado = doc["bm25_score"] / max_bm25 if max_bm25 > 0 else 0
        if doc["id"] in scores_combinados:
            scores_combinados[doc["id"]]["bm25_score"] = bm25_normalizado
        else:
            scores_combinados[doc["id"]] = {
                "doc": doc,
                "vector_score": 0.0,
                "bm25_score": bm25_normalizado
            }
    
    # Score final híbrido
    resultados = []
    for id, item in scores_combinados.items():
        score_final = (alpha * item["vector_score"]) + ((1 - alpha) * item["bm25_score"])
        resultados.append({
            **item["doc"],
            "hybrid_score": score_final,
            "vector_score": item["vector_score"],
            "bm25_score": item["bm25_score"]
        })
    
    return sorted(resultados, key=lambda x: x["hybrid_score"], reverse=True)[:limite]

if __name__ == "__main__":
    pergunta = "Como faço para devolver um produto com defeito?"
    print(f"Pergunta: {pergunta}\n")
    
    resultados = hybrid_search(pergunta, limite=3, alpha=0.7)
    
    print(f"{len(resultados)} chunks encontrados:\n")
    for doc in resultados:
        print(f"Fonte: {doc['metadata']['fonte']}")
        print(f"Conteúdo: {doc['content'][:100]}...")
        print(f"Score híbrido: {doc['hybrid_score']:.4f} | Vetorial: {doc['vector_score']:.4f} | BM25: {doc['bm25_score']:.4f}\n")