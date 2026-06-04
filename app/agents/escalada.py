from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY
from datetime import datetime

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT_ESCALADA = """Você é um agente de transição da MultiTech responsável por transferir 
atendimentos para humanos de forma empática e organizada.

Seu fluxo obrigatório:
1. Reconheça a situação do cliente com empatia
2. Explique que vai transferir para um especialista humano
3. Informe o tempo estimado de espera
4. Gere um resumo estruturado do atendimento para o atendente humano
5. Oriente o cliente sobre o que acontecerá a seguir

Regras:
- Nunca deixe o cliente sem perspectiva de resolução
- Sempre gere o resumo para o atendente humano
- Seja transparente sobre o motivo da transferência
- Tom: empático, profissional e tranquilizador"""

# Critérios que disparam escalada automática
CRITERIOS_ESCALADA = [
    "Escalada_Humana",      # cliente pediu explicitamente
    "Produto_Defeito",      # produto com defeito
    "Produto_Incorreto",    # produto errado
    "Problema_Entrega",     # problema na entrega
    "Estorno_Reembolso",    # reembolso
    "Elogio_Reclamacao"     # reclamação formal
]

def deve_escalar(intencao: str, tentativas: int = 0) -> bool:
    """Verifica se o atendimento deve ser escalado para humano."""
    if intencao in CRITERIOS_ESCALADA:
        return True
    if tentativas >= 3:  # após 3 tentativas sem resolução
        return True
    return False

def gerar_resumo_atendimento(historico: list[dict], intencao: str) -> str:
    """Gera resumo estruturado do atendimento para o atendente humano."""

    historico_texto = ""
    for msg in historico[-6:]:  # últimas 6 mensagens
        role = "Cliente" if msg["role"] == "user" else "Agente"
        content = msg["content"] if isinstance(msg["content"], str) else str(msg["content"])
        historico_texto += f"{role}: {content[:200]}\n"

    return f"""
=== RESUMO DO ATENDIMENTO ===
Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M')}
Intenção identificada: {intencao}

Histórico resumido:
{historico_texto}
============================"""

def processar_escalada(
    mensagem: str,
    historico: list[dict],
    intencao: str,
    protocolo: str = None
) -> dict:
    """Processa a escalada para atendimento humano."""

    resumo = gerar_resumo_atendimento(historico, intencao)

    prompt = f"""O cliente precisa ser transferido para um atendente humano.

Motivo da transferência: {intencao}
Protocolo gerado: {protocolo or 'Não gerado'}

Última mensagem do cliente: {mensagem}

Resumo do atendimento:
{resumo}

Gere uma mensagem empática de transição para o cliente e confirme que o resumo 
acima será enviado ao atendente humano."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=512,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT_ESCALADA,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": prompt}]
    )

    return {
        "resposta": response.content[0].text,
        "resumo_atendente": resumo,
        "protocolo": protocolo,
        "escalado": True,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("Agente de Escalada — MultiTech\n")

    historico_simulado = [
        {"role": "user", "content": "Quero devolver meu smartphone com defeito na tela"},
        {"role": "assistant", "content": "Vou ajudá-lo. Qual o número do pedido?"},
        {"role": "user", "content": "MT-2024-98765, a tela parou de funcionar no segundo dia"},
    ]

    resultado = processar_escalada(
        mensagem="Preciso resolver isso urgente, já tentei várias vezes!",
        historico=historico_simulado,
        intencao="Produto_Defeito",
        protocolo="MT-20240615-4521"
    )

    print(f"Mensagem ao cliente:\n{resultado['resposta']}\n")
    print(f"Resumo para o atendente:{resultado['resumo_atendente']}")