from anthropic import Anthropic
from app.rag.reranker import buscar_e_rerankar
from app.rag.retriever import formatar_contexto
from app.config import ANTHROPIC_API_KEY
import json

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT_POS_VENDA = """Você é um agente de pós-venda da MultiTech especializado em trocas e devoluções.

Seu fluxo obrigatório:
1. Colete o número do pedido
2. Colete a descrição do problema
3. Verifique elegibilidade conforme política (prazo, condições)
4. Registre o protocolo de atendimento
5. Oriente os próximos passos

Regras:
- NUNCA aprove devolução sem coletar número do pedido
- NUNCA invente prazos ou políticas — use apenas o contexto fornecido
- Se o caso for complexo ou o cliente estiver insatisfeito, escale para humano
- Gere sempre um número de protocolo no formato: MT-YYYYMMDD-XXXX"""

# Tools que o agente pode usar
TOOLS = [
    {
        "name": "registrar_protocolo",
        "description": "Registra um protocolo de atendimento para troca ou devolução",
        "input_schema": {
            "type": "object",
            "properties": {
                "numero_pedido": {
                    "type": "string",
                    "description": "Número do pedido do cliente"
                },
                "tipo": {
                    "type": "string",
                    "enum": ["troca", "devolucao", "defeito"],
                    "description": "Tipo de solicitação"
                },
                "descricao": {
                    "type": "string",
                    "description": "Descrição do problema relatado pelo cliente"
                },
                "escalar_humano": {
                    "type": "boolean",
                    "description": "Se true, escala para atendente humano"
                }
            },
            "required": ["numero_pedido", "tipo", "descricao", "escalar_humano"]
        }
    }
]

def processar_tool(tool_name: str, tool_input: dict) -> str:
    """Processa a chamada de tool do agente."""

    if tool_name == "registrar_protocolo":
        import random
        from datetime import datetime

        numero = f"MT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000,9999)}"

        resultado = {
            "protocolo": numero,
            "numero_pedido": tool_input["numero_pedido"],
            "tipo": tool_input["tipo"],
            "status": "REGISTRADO",
            "escalar_humano": tool_input["escalar_humano"],
            "mensagem": f"Protocolo {numero} registrado com sucesso."
        }

        if tool_input["escalar_humano"]:
            resultado["mensagem"] += " Caso encaminhado para atendente humano."

        return json.dumps(resultado, ensure_ascii=False)

    return json.dumps({"erro": "Tool não encontrada"})

def processar_pos_venda(mensagem: str, historico: list[dict]) -> dict:
    """Agente de pós-venda com Tool Calling."""

    # 1. Busca contexto RAG
    documentos = buscar_e_rerankar(mensagem, limite=3)
    contexto = formatar_contexto(documentos)

    mensagem_atual = f"""Contexto da política da MultiTech:
{contexto}

Mensagem do cliente:
{mensagem}"""

    mensagens = historico + [{"role": "user", "content": mensagem_atual}]
    escalar = False
    protocolo = None

    # 2. Loop de Tool Calling
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=[{
                "type": "text",
                "text": SYSTEM_PROMPT_POS_VENDA,
                "cache_control": {"type": "ephemeral"}
            }],
            tools=TOOLS,
            messages=mensagens
        )

        # 3. Verifica se o agente quer usar uma tool
        if response.stop_reason == "tool_use":
            tool_block = next(b for b in response.content if b.type == "tool_use")
            tool_result = processar_tool(tool_block.name, tool_block.input)
            result_json = json.loads(tool_result)

            if result_json.get("escalar_humano"):
                escalar = True
            if result_json.get("protocolo"):
                protocolo = result_json["protocolo"]

            # Adiciona resultado da tool ao histórico
            mensagens = mensagens + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": tool_result
                }]}
            ]
            continue

        # 4. Resposta final do agente
        resposta_texto = next(
            (b.text for b in response.content if hasattr(b, "text")), ""
        )
        break

    historico_atualizado = mensagens + [
        {"role": "assistant", "content": resposta_texto}
    ]

    return {
        "resposta": resposta_texto,
        "protocolo": protocolo,
        "escalar_humano": escalar,
        "historico": historico_atualizado
    }

if __name__ == "__main__":
    print("Agente Pós-Venda — MultiTech\n")

    cenarios = [
        {
            "nome": "Devolução com pedido",
            "msgs": [
                "Quero devolver meu smartphone, chegou com defeito na tela",
                "O número do pedido é MT-2024-98765"
            ]
        }
    ]

    for cenario in cenarios:
        print(f"Cenário: {cenario['nome']}")
        print("=" * 60)
        historico = []

        for msg in cenario["msgs"]:
            print(f"Cliente: {msg}")
            resultado = processar_pos_venda(msg, historico)
            historico = resultado["historico"]
            print(f"Agente: {resultado['resposta']}")
            if resultado["protocolo"]:
                print(f"Protocolo gerado: {resultado['protocolo']}")
            if resultado["escalar_humano"]:
                print("⚠️  ESCALANDO PARA HUMANO")
            print("-" * 60)