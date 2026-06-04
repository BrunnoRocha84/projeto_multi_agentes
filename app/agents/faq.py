from anthropic import Anthropic
from app.rag.reranker import buscar_e_rerankar
from app.rag.retriever import formatar_contexto
from app.config import ANTHROPIC_API_KEY

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT_FAQ = """Você é um agente de atendimento ao cliente da MultiTech.

Regras obrigatórias:
- Responda APENAS com base no contexto fornecido
- NUNCA invente informações
- Cite sempre a fonte (ex: "Conforme nossa política de devolução...")
- Se a informação não estiver no contexto, diga: "Não encontrei essa informação. Ligue: 0800 123 4567"
- Seja cordial e objetivo
- Identifique se o caso precisa de atendimento humano"""

def responder_faq(pergunta: str, historico: list[dict]) -> dict:
    """Responde dúvidas usando RAG + histórico de conversa."""

    # 1. Busca contexto com pipeline completo
    documentos = buscar_e_rerankar(pergunta, limite=3)
    contexto = formatar_contexto(documentos)

    # 2. Monta mensagem com contexto — será cacheada quando > 1024 tokens
    mensagem_atual = f"""Contexto dos documentos internos da MultiTech:
{contexto}

Pergunta do cliente:
{pergunta}

Responda com base exclusivamente no contexto acima."""

    # 3. Adiciona ao histórico
    mensagens = historico + [{"role": "user", "content": mensagem_atual}]

    # 4. Chama Claude com cache no system prompt
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT_FAQ,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=mensagens
    )

    resposta_texto = response.content[0].text
    fontes = list(set([doc["metadata"]["fonte"] for doc in documentos]))
    uso = response.usage

    # 5. Atualiza histórico
    historico_atualizado = mensagens + [
        {"role": "assistant", "content": resposta_texto}
    ]

    return {
        "resposta": resposta_texto,
        "fontes": fontes,
        "tokens_usados": uso.input_tokens + uso.output_tokens,
        "cache_lido": getattr(uso, "cache_read_input_tokens", 0),
        "historico": historico_atualizado
    }

if __name__ == "__main__":
    print("Agente FAQ — MultiTech\n")

    historico = []

    perguntas = [
        "Como faço para devolver um produto com defeito?",
        "Qual o prazo para devolução?",
        "E se eu não tiver a nota fiscal?"
    ]

    for pergunta in perguntas:
        print(f"Cliente: {pergunta}")
        resultado = responder_faq(pergunta, historico)
        historico = resultado["historico"]
        print(f"Agente: {resultado['resposta']}")
        print(f"Fontes: {resultado['fontes']}")
        print(f"Tokens: {resultado['tokens_usados']} | Cache lido: {resultado['cache_lido']}\n")
        print("-" * 60)