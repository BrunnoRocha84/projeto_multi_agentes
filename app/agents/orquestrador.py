from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

from app.agents.triagem import classificar_intencao
from app.agents.faq import responder_faq
from app.agents.pos_venda import processar_pos_venda
from app.agents.escalada import processar_escalada, deve_escalar

# ─────────────────────────────────────────
# ESTADO DO GRAFO
# ─────────────────────────────────────────
class EstadoAtendimento(TypedDict):
    mensagem: str
    intencao: str
    historico: Annotated[list, operator.add]
    resposta: str
    protocolo: str
    escalado: bool
    tentativas: int

# ─────────────────────────────────────────
# NÓS DO GRAFO
# ─────────────────────────────────────────
def no_triagem(estado: EstadoAtendimento) -> dict:
    """Nó 1: Classifica a intenção do cliente."""
    intencao = classificar_intencao(estado["mensagem"])
    print(f"[Triagem] Intenção: {intencao}")
    return {"intencao": intencao}

def no_faq(estado: EstadoAtendimento) -> dict:
    """Nó 2: Responde dúvidas com RAG."""
    resultado = responder_faq(estado["mensagem"], estado["historico"])
    print(f"[FAQ] Tokens: {resultado['tokens_usados']}")
    return {
        "resposta": resultado["resposta"],
        "historico": resultado["historico"]
    }

def no_pos_venda(estado: EstadoAtendimento) -> dict:
    """Nó 3: Processa trocas e devoluções."""
    resultado = processar_pos_venda(estado["mensagem"], estado["historico"])
    print(f"[Pós-Venda] Protocolo: {resultado.get('protocolo')}")
    return {
        "resposta": resultado["resposta"],
        "protocolo": resultado.get("protocolo", ""),
        "escalado": resultado.get("escalar_humano", False),
        "historico": resultado["historico"]
    }

def no_escalada(estado: EstadoAtendimento) -> dict:
    """Nó 4: Escala para atendente humano."""
    resultado = processar_escalada(
        mensagem=estado["mensagem"],
        historico=estado["historico"],
        intencao=estado["intencao"],
        protocolo=estado.get("protocolo")
    )
    print(f"[Escalada] Transferindo para humano")
    return {
        "resposta": resultado["resposta"],
        "escalado": True,
        "historico": [{"role": "assistant", "content": resultado["resposta"]}]
    }

def no_saudacao(estado: EstadoAtendimento) -> dict:
    """Nó 5: Responde saudações."""
    return {
        "resposta": "Olá! Bem-vindo ao atendimento da MultiTech! 😊 Como posso ajudá-lo hoje?",
        "historico": [{"role": "assistant", "content": "Olá! Bem-vindo ao atendimento da MultiTech! 😊 Como posso ajudá-lo hoje?"}]
    }

def no_encerramento(estado: EstadoAtendimento) -> dict:
    """Nó 6: Encerra o atendimento."""
    return {
        "resposta": "Foi um prazer ajudá-lo! Qualquer dúvida, estamos disponíveis 24h. Tenha um ótimo dia! 👋",
        "historico": [{"role": "assistant", "content": "Foi um prazer ajudá-lo!"}]
    }

# ─────────────────────────────────────────
# ROTEADOR
# ─────────────────────────────────────────
def rotear(estado: EstadoAtendimento) -> str:
    """Decide qual agente ativar com base na intenção."""
    intencao = estado["intencao"]

    if intencao == "Saudacao":
        return "saudacao"
    if intencao == "Encerramento":
        return "encerramento"
    if deve_escalar(intencao, estado.get("tentativas", 0)):
        return "escalada"
    if intencao in ["Solicitar_Troca", "Devolver_Produto", "Produto_Defeito",
                    "Produto_Incorreto", "Estorno_Reembolso"]:
        return "pos_venda"
    return "faq"

# ─────────────────────────────────────────
# CONSTRUÇÃO DO GRAFO
# ─────────────────────────────────────────
def criar_grafo():
    grafo = StateGraph(EstadoAtendimento)

    # Adiciona nós
    grafo.add_node("triagem", no_triagem)
    grafo.add_node("faq", no_faq)
    grafo.add_node("pos_venda", no_pos_venda)
    grafo.add_node("escalada", no_escalada)
    grafo.add_node("saudacao", no_saudacao)
    grafo.add_node("encerramento", no_encerramento)

    # Ponto de entrada
    grafo.set_entry_point("triagem")

    # Roteamento condicional após triagem
    grafo.add_conditional_edges(
        "triagem",
        rotear,
        {
            "faq": "faq",
            "pos_venda": "pos_venda",
            "escalada": "escalada",
            "saudacao": "saudacao",
            "encerramento": "encerramento"
        }
    )

    # Todos os nós terminam no END
    grafo.add_edge("faq", END)
    grafo.add_edge("pos_venda", END)
    grafo.add_edge("escalada", END)
    grafo.add_edge("saudacao", END)
    grafo.add_edge("encerramento", END)

    return grafo.compile()

# ─────────────────────────────────────────
# INTERFACE DE ATENDIMENTO
# ─────────────────────────────────────────
app_grafo = criar_grafo()

def atender(mensagem: str, historico: list[dict] = None) -> dict:
    """Função principal de atendimento via grafo multi-agentes."""
    estado_inicial = {
        "mensagem": mensagem,
        "intencao": "",
        "historico": historico or [],
        "resposta": "",
        "protocolo": "",
        "escalado": False,
        "tentativas": 0
    }
    return app_grafo.invoke(estado_inicial)

if __name__ == "__main__":
    print("MultiTech — Sistema Multi-Agentes\n")
    print("=" * 60)

    cenarios = [
        "Oi, boa tarde!",
        "Quero devolver meu smartphone com defeito",
        "Qual o prazo de entrega para Belo Horizonte?",
        "Preciso falar com um atendente humano",
        "Obrigado, tchau!"
    ]

    historico = []
    for mensagem in cenarios:
        print(f"\nCliente: {mensagem}")
        resultado = atender(mensagem, historico)
        historico = resultado.get("historico", historico)
        print(f"Agente: {resultado['resposta']}")
        if resultado.get("protocolo"):
            print(f"Protocolo: {resultado['protocolo']}")
        if resultado.get("escalado"):
            print("⚠️  ESCALADO PARA HUMANO")
        print("-" * 60)