## O que faz: cria o módulo que recebe a pergunta do cliente, transforma em embedding e busca os chunks mais relevantes no Supabase — é o coração do RAG.
from app.rag.embeddings import gerar_embedding
from app.config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client

# Conecta ao Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def buscar_documentos(pergunta: str, limite: int = 3) -> list[dict]:
    """Busca os chunks mais relevantes para a pergunta."""
    
    # 1. Transforma a pergunta em embedding
    embedding = gerar_embedding(pergunta)
    
    # 2. Busca por similaridade no Supabase
    resultado = supabase.rpc("buscar_documentos", {
        "query_embedding": embedding,
        "match_count": limite
    }).execute()
    
    return resultado.data

def formatar_contexto(documentos: list[dict]) -> str:
    """Formata os chunks recuperados em texto para o prompt."""
    
    contexto = ""
    for doc in documentos:
        fonte = doc["metadata"]["fonte"]
        contexto += f"\n[Fonte: {fonte}]\n{doc['content']}\n"
    
    return contexto.strip()

if __name__ == "__main__":
    pergunta = "Como faço para devolver um produto com defeito?"
    
    print(f"Pergunta: {pergunta}\n")
    docs = buscar_documentos(pergunta)
    
    print(f"{len(docs)} chunks encontrados:\n")
    for doc in docs:
        print(f"Fonte: {doc['metadata']['fonte']}")
        print(f"Conteúdo: {doc['content'][:100]}...")
        print(f"Similaridade: {doc['similarity']:.4f}\n")