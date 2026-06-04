## faz: cria o módulo responsável por ler os documentos, dividir em chunks e salvar os embeddings no Supabase — é a etapa de indexação do RAG
# Como faz: Lê cada documento markdown 
# Chunking — divide em pedaços de 500 caracteres com overlap de 50 para não perder contexto entre chunks
# Embedding — transforma cada chunk em vetor
# Salva no Supabase com metadata para rastreabilidade

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.rag.embeddings import gerar_embedding
from app.config import SUPABASE_URL, SUPABASE_KEY
from supabase import create_client
import os

# Conecta ao Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configuração do chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "]
)

def carregar_documento(caminho: str, nome: str) -> int:
    """Carrega um documento, divide em chunks e salva no Supabase."""
    
    # 1. Lê o documento
    loader = TextLoader(caminho, encoding="utf-8")
    documentos = loader.load()
    
    # 2. Divide em chunks
    chunks = text_splitter.split_documents(documentos)
    print(f"{nome}: {len(chunks)} chunks gerados")
    
    # 3. Gera embeddings e salva no Supabase
    for i, chunk in enumerate(chunks):
        embedding = gerar_embedding(chunk.page_content)
        
        supabase.table("documents").insert({
            "content": chunk.page_content,
            "metadata": {"fonte": nome, "chunk": i},
            "embedding": embedding
        }).execute()
    
    print(f"{nome}: salvo no Supabase com sucesso")
    return len(chunks)

if __name__ == "__main__":
    docs_dir = "docs"
    arquivos = {
        "politica_devolucao": "politica_devolucao.md",
        "manual_smartphone": "manual_smartphone.md",
        "faq_clientes": "faq_clientes.md"
    }
    
    total = 0
    for nome, arquivo in arquivos.items():
        caminho = os.path.join(docs_dir, arquivo)
        total += carregar_documento(caminho, nome)
    
    print(f"\nTotal de chunks indexados: {total}")