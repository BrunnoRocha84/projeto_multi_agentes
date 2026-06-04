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
- Identifique quando o caso precisa de atendimento humano e sinalize claramente"""

def responder(pergunta: str, historico: list[dict]) -> dict:
    """Recebe pergunta e histórico da conversa, retorna resposta fundamentada."""
    
    # 1. Busca contexto relevante com Hybrid Search + Reranker
    documentos = buscar_e_rerankar(pergunta, limite=3)
    contexto = formatar_contexto(documentos)
    
    # 2. Monta mensagem atual com contexto
    mensagem_atual = f"""Contexto dos documentos internos da MultiTech:
{contexto}

Pergunta do cliente:
{pergunta}

Responda com base exclusivamente no contexto acima."""
    
    # 3. Adiciona mensagem atual ao histórico
    mensagens = historico + [{"role": "user", "content": mensagem_atual}]
    
    # 4. Chama o Claude com histórico completo
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=mensagens
    )
    
    resposta_texto = response.content[0].text
    fontes = list(set([doc["metadata"]["fonte"] for doc in documentos]))
    
    # 5. Atualiza histórico com pergunta e resposta
    historico_atualizado = mensagens + [
        {"role": "assistant", "content": resposta_texto}
    ]
    
    return {
        "resposta": resposta_texto,
        "fontes": fontes,
        "tokens_usados": response.usage.input_tokens + response.usage.output_tokens,
        "historico": historico_atualizado
    }

if __name__ == "__main__":
    import threading

    print("MultiTech — Atendimento ao Cliente")
    print("Digite 'sair' para encerrar\n")

    historico = []
    buffer_mensagens = []
    timer = None
    TEMPO_ESPERA = 6  # segundos de inatividade antes de processar

    def processar_buffer():
        """Processa todas as mensagens acumuladas no buffer."""
        global buffer_mensagens, historico

        if not buffer_mensagens:
            return

        # Junta todas as mensagens fragmentadas em uma só
        pergunta_completa = " ".join(buffer_mensagens)
        buffer_mensagens = []

        print(f"\n[Processando]: {pergunta_completa}")
        resultado = responder(pergunta_completa, historico)
        historico = resultado["historico"]

        print(f"\nAgente: {resultado['resposta']}")
        print(f"Fontes: {resultado['fontes']}")
        print(f"Tokens usados: {resultado['tokens_usados']}\n")

    def receber_mensagem(texto: str):
        """Adiciona mensagem ao buffer e reinicia o timer."""
        global timer

        buffer_mensagens.append(texto)

        # Cancela o timer anterior se ainda não disparou
        if timer is not None:
            timer.cancel()

        # Inicia novo timer — só processa após TEMPO_ESPERA segundos de silêncio
        timer = threading.Timer(TEMPO_ESPERA, processar_buffer)
        timer.start()

    while True:
        entrada = input("Cliente: ").strip()

        if entrada.lower() == "sair":
            if timer is not None:
                timer.cancel()
            print("Atendimento encerrado.")
            break

        if not entrada:
            continue

        receber_mensagem(entrada)