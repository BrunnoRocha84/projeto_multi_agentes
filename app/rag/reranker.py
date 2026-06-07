## CrossEncoder — modelo que avalia o par (pergunta + chunk) junto, muito mais preciso que embeddings separados
## buscar_e_rerankar() — pipeline completo: busca 6 candidatos com Hybrid Search e o reranker seleciona os 3 melhores
## Busca mais ampla (limite * 2) para dar mais opções ao reranker escolher

from sentence_transformers import CrossEncoder
from app.rag.hybrid_search import hybrid_search

# ─────────────────────────────────────────
# SINGLETON — carrega o modelo uma vez só
# ─────────────────────────────────────────
_model = None

def get_model() -> CrossEncoder:
    """Retorna o modelo CrossEncoder, carregando uma unica vez."""
    global _model
    if _model is None:
        print("[Reranker] Carregando modelo CrossEncoder...")
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        print("[Reranker] Modelo carregado e em cache.")
    return _model

def rerankar(pergunta: str, documentos: list[dict]) -> list[dict]:
    """Reordena os chunks usando Cross Encoder."""
    model = get_model()
    pares = [(pergunta, doc["content"]) for doc in documentos]
    scores = model.predict(pares)
    for i, doc in enumerate(documentos):
        doc["rerank_score"] = float(scores[i])
    return sorted(documentos, key=lambda x: x["rerank_score"], reverse=True)

def buscar_e_rerankar(pergunta: str, limite: int = 3) -> list[dict]:
    """Pipeline completo: Hybrid Search + Reranking."""
    candidatos = hybrid_search(pergunta, limite=limite * 2)
    rerankeados = rerankar(pergunta, candidatos)
    return rerankeados[:limite]

if __name__ == "__main__":
    pergunta = "Como faço para devolver um produto com defeito?"
    print(f"Pergunta: {pergunta}\n")
    resultados = buscar_e_rerankar(pergunta, limite=3)
    print(f"{len(resultados)} chunks após reranking:\n")
    for doc in resultados:
        print(f"Fonte: {doc['metadata']['fonte']}")
        print(f"Conteudo: {doc['content'][:100]}...")
        print(f"Rerank score: {doc['rerank_score']:.4f} | Hibrido: {doc['hybrid_score']:.4f}\n")