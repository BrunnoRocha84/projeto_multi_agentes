## CrossEncoder — modelo que avalia o par (pergunta + chunk) junto, muito mais preciso que embeddings separados
## buscar_e_rerankar() — pipeline completo: busca 6 candidatos com Hybrid Search e o reranker seleciona os 3 melhores
## Busca mais ampla (limite * 2) para dar mais opções ao reranker escolher

from sentence_transformers import CrossEncoder
from app.rag.hybrid_search import hybrid_search

# Modelo de reranking
model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerankar(pergunta: str, documentos: list[dict]) -> list[dict]:
    """Reordena os chunks usando Cross Encoder."""
    
    # Cria pares (pergunta, chunk) para o modelo avaliar
    pares = [(pergunta, doc["content"]) for doc in documentos]
    
    # Modelo avalia cada par e retorna scores
    scores = model.predict(pares)
    
    # Adiciona score e reordena
    for i, doc in enumerate(documentos):
        doc["rerank_score"] = float(scores[i])
    
    return sorted(documentos, key=lambda x: x["rerank_score"], reverse=True)

def buscar_e_rerankar(pergunta: str, limite: int = 3) -> list[dict]:
    """Pipeline completo: Hybrid Search + Reranking."""
    
    # 1. Busca candidatos com Hybrid Search (busca mais ampla)
    candidatos = hybrid_search(pergunta, limite=limite * 2)
    
    # 2. Reranker avalia e reordena
    rerankeados = rerankar(pergunta, candidatos)
    
    # 3. Retorna apenas os melhores
    return rerankeados[:limite]

if __name__ == "__main__":
    pergunta = "Como faço para devolver um produto com defeito?"
    print(f"Pergunta: {pergunta}\n")
    
    resultados = buscar_e_rerankar(pergunta, limite=3)
    
    print(f"{len(resultados)} chunks após reranking:\n")
    for doc in resultados:
        print(f"Fonte: {doc['metadata']['fonte']}")
        print(f"Conteúdo: {doc['content'][:100]}...")
        print(f"Rerank score: {doc['rerank_score']:.4f} | Híbrido: {doc['hybrid_score']:.4f}\n")