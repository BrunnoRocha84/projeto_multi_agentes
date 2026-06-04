from openai import OpenAI
from app.config import OPENAI_API_KEY

# Cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Modelo de embeddings
MODELO_EMBEDDING = "text-embedding-3-small"
DIMENSOES = 1536

def gerar_embedding(texto: str) -> list[float]:
    """Transforma um texto em vetor de embeddings usando OpenAI."""
    response = client.embeddings.create(
        input=texto,
        model=MODELO_EMBEDDING
    )
    return response.data[0].embedding

if __name__ == "__main__":
    texto = "Cliente quer devolver um iPhone 15 com defeito na câmera."
    vetor = gerar_embedding(texto)
    print(f"Dimensões: {len(vetor)}")
    print(f"Primeiros 5 valores: {vetor[:5]}")