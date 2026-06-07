from openai import OpenAI
from app.config import OPENAI_API_KEY
import hashlib

client = OpenAI(api_key=OPENAI_API_KEY)

MODELO_EMBEDDING = "text-embedding-3-small"
DIMENSOES = 1536

# Cache de embeddings — evita chamar a API para textos repetidos
_cache_embeddings = {}

def gerar_embedding(texto: str) -> list[float]:
    """Transforma texto em vetor, usando cache para evitar chamadas repetidas."""
    
    # Cria chave de cache baseada no hash do texto
    chave = hashlib.md5(texto.encode()).hexdigest()
    
    if chave in _cache_embeddings:
        return _cache_embeddings[chave]
    
    response = client.embeddings.create(
        input=texto,
        model=MODELO_EMBEDDING
    )
    
    embedding = response.data[0].embedding
    _cache_embeddings[chave] = embedding
    return embedding

if __name__ == "__main__":
    texto = "Cliente quer devolver um iPhone 15 com defeito na câmera."
    
    import time
    
    inicio = time.time()
    vetor = gerar_embedding(texto)
    print(f"1a chamada: {int((time.time()-inicio)*1000)}ms | Dimensões: {len(vetor)}")
    
    inicio = time.time()
    vetor = gerar_embedding(texto)
    print(f"2a chamada (cache): {int((time.time()-inicio)*1000)}ms | Dimensões: {len(vetor)}")