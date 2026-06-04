## o primeiro agente do projeto — ele vai receber a pergunta do cliente, buscar o contexto com o pipeline RAG
from anthropic import Anthropic
from app.rag.reranker import buscar_e_rerankar
from app.rag.retriever import formatar_contexto
from app.config import ANTHROPIC_API_KEY

# Cliente Anthropic
client = Anthropic(api_key=ANTHROPIC_API_KEY)

# System prompt do agente
SYSTEM_PROMPT = """Você é um agente de atendimento ao cliente da MultiTech, 
uma empresa de produtos tecnológicos.

Suas responsabilidades:
- Responder dúvidas sobre produtos, pedidos e políticas da empresa
- Basear TODAS as respostas nos documentos fornecidos no contexto
- Ser cordial, objetivo e preciso
- Caso a informação não esteja no contexto, dizer claramente que não possui essa informação

Regras importantes:
- NUNCA invente informações que não estejam no contexto
- SEMPRE cite a fonte da informação (ex: "Conforme nossa política de devolução...")
- Se não souber responder, oriente o cliente a entrar em contato pelo 0800 123 4567
- Nunca responda perguntas que não estejam relacionadas aos produtos, pedidos ou políticas da MultiTech, e caso aconteça, o seja cordial ao informar que só pode ajudar com questões relacionadas à empresa.
- Identifique quando o caso precisa de atendimento humano e sinalize claramente"""


def responder(pergunta: str) -> dict:
    """Recebe pergunta do cliente e retorna resposta fundamentada no RAG."""
    
    # 1. Busca contexto relevante com Hybrid Search + Reranker
    documentos = buscar_e_rerankar(pergunta, limite=3)
    contexto = formatar_contexto(documentos)
    
    # 2. Monta o prompt com contexto
    prompt = f"""Contexto dos documentos internos da MultiTech:
{contexto}

Pergunta do cliente:
{pergunta}

Responda com base exclusivamente no contexto acima."""
    
    # 3. Chama o Claude
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    
    # 4. Retorna resposta e fontes usadas
    fontes = list(set([doc["metadata"]["fonte"] for doc in documentos]))
    
    return {
        "resposta": response.content[0].text,
        "fontes": fontes,
        "tokens_usados": response.usage.input_tokens + response.usage.output_tokens
    }

if __name__ == "__main__":
    perguntas = [
        "Como faço para devolver um produto com defeito?",
        "Quais formas de pagamento vocês aceitam?",
        "Meu smartphone está superaquecendo, o que fazer?"
    ]
    
    for pergunta in perguntas:
        print(f"\nCliente: {pergunta}")
        print("-" * 60)
        resultado = responder(pergunta)
        print(f"Agente: {resultado['resposta']}")
        print(f"Fontes: {resultado['fontes']}")
        print(f"Tokens usados: {resultado['tokens_usados']}")
        print("=" * 60)