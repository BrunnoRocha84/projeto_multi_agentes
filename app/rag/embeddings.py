## O que faz: cria o módulo responsável por transformar texto em vetores — será usado em todo o pipeline de RAG.

from sentence_transformers import SentenceTransformer

# Carrega o modelo de embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

def gerar_embedding(texto: str) -> list[float]:
    """Transforma um texto em vetor de embeddings."""
    embedding = model.encode(texto)
    return embedding.tolist()

if __name__ == "__main__":
    texto = "Cliente quer devolver um iPhone 15 com defeito na câmera."
    vetor = gerar_embedding(texto)
    print(f"Dimensões: {len(vetor)}")
    print(f"Primeiros 5 valores: {vetor[:5]}")