from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY

client = Anthropic(api_key=ANTHROPIC_API_KEY)

# Intenções suportadas pelo sistema
INTENCOES = [
    "Saudacao",
    "Encerramento",
    "Escalada_Humana",
    "Elogio_Reclamacao",
    "Informacao_Produto",
    "Rastrear_Pedido",
    "Prazo_Entrega",
    "Alterar_Endereco",
    "Problema_Entrega",
    "Solicitar_Troca",
    "Devolver_Produto",
    "Produto_Defeito",
    "Produto_Incorreto",
    "Estorno_Reembolso",
    "Recuperar_Senha",
    "Erro_Sistema",
    "Duvida_Geral"
]

SYSTEM_PROMPT_TRIAGEM = """Você é um classificador de intenções de atendimento ao cliente da MultiTech.

Sua única função é identificar a intenção da mensagem do cliente e retornar APENAS o nome da intenção.

Intenções disponíveis:
- Saudacao: cumprimentos e início de conversa
- Encerramento: despedidas e finalização
- Escalada_Humana: quer falar com atendente humano
- Elogio_Reclamacao: feedback positivo ou negativo
- Informacao_Produto: dúvidas sobre produtos
- Rastrear_Pedido: localizar entrega
- Prazo_Entrega: consultar tempo de frete
- Alterar_Endereco: mudar endereço de entrega
- Problema_Entrega: atraso ou extravio
- Solicitar_Troca: trocar produto
- Devolver_Produto: devolver produto
- Produto_Defeito: produto com defeito
- Produto_Incorreto: produto errado recebido
- Estorno_Reembolso: solicitar reembolso
- Recuperar_Senha: resetar senha
- Erro_Sistema: bug no site ou app
- Duvida_Geral: qualquer outra dúvida

Responda APENAS com o nome exato da intenção, sem explicações."""


def classificar_intencao(mensagem: str) -> str:
    """Classifica a intenção usando Prompt Caching para economizar tokens."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=50,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT_TRIAGEM,
                "cache_control": {"type": "ephemeral"}
            }
        ],
        messages=[{"role": "user", "content": mensagem}]
    )

    intencao = response.content[0].text.strip()

    uso = response.usage
    print(f"[Cache] Input: {uso.input_tokens} | "
          f"Cache criado: {getattr(uso, 'cache_creation_input_tokens', 0)} | "
          f"Cache lido: {getattr(uso, 'cache_read_input_tokens', 0)}")

    if intencao not in INTENCOES:
        return "Duvida_Geral"

    return intencao


if __name__ == "__main__":
    testes = [
        "Oi, boa tarde!",
        "Quero devolver meu smartphone",
        "Meu produto chegou quebrado",
        "Cadê meu pedido?",
        "Preciso falar com um humano",
        "Qual o prazo de entrega para SP?",
        "Quero cancelar minha compra"
    ]

    for msg in testes:
        intencao = classificar_intencao(msg)
        print(f"Mensagem: {msg}")
        print(f"Intenção: {intencao}\n")