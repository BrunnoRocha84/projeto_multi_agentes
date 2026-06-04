from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
import time

from app.agents.triagem import classificar_intencao
from app.agents.faq import responder_faq
from app.agents.pos_venda import processar_pos_venda
from app.agents.escalada import processar_escalada, deve_escalar
from app.observability.langfuse_client import registrar_atendimento

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
    tokens_usados: int
    latencia_ms: int
    fontes: list
    usuario_id: str

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
    inicio = time.time()
    resultado = responder_faq(estado["mensagem"], estado["historico"])
    latencia = int((time.time() - inicio) * 1000)
    print(f"[FAQ] Tokens: {resultado['tokens_usados']} | Latência: {latencia}ms")
    return {
        "resposta": resultado["resposta"],
        "historico": resultado["historico"],
        "tokens_usados": resultado["tokens_usados"],
        "latencia_ms": latencia,
        "fontes": resultado.get("fontes", [])
    }

def no_pos_venda(estado: EstadoAtendimento) -> dict:
    """Nó 3: Processa trocas e devoluções."""
    inicio = time.time()
    resultado = processar_pos_venda(estado["mensagem"], estado["historico"])
    latencia = int((time.time() - inicio) * 1000)
    print(f"[Pós-Venda] Protocolo: {resultado.get('protocolo')} | Latência: {latencia}ms")
    return {
        "resposta": resultado["resposta"],
        "protocolo": resultado.get("protocolo", ""),
        "escalado": resultado.get("escalar_humano", False),
        "historico": resultado["historico"],
        "latencia_ms": latencia
    }

def no_escalada(estado: EstadoAtendimento) -> dict:
    """Nó 4: Escala para atendente humano."""
    resultado = processar_escalada(
        mensagem=estado["mensagem"],
        historico=estado["historico"],
        intencao=estado["intencao"],
        protocolo=estado.get("protocolo")
    )
    print("[Escalada] Transferindo para humano")
    return {
        "resposta": resultado["resposta"],
        "escalado": True,
        "historico": [{"role": "assistant", "content": resultado["resposta"]}]
    }

def no_saudacao(estado: EstadoAtendimento) -> dict:
    """Nó 5: Responde saudações."""
    resposta = "Olá! Bem-vindo ao atendimento da MultiTech! 😊 Como posso ajudá-lo hoje?"
    return {
        "resposta": resposta,
        "historico": [{"role": "assistant", "content": resposta}]
    }

def no_encerramento(estado: EstadoAtendimento) -> dict:
    """Nó 6: Encerra o atendimento."""
    resposta = "Foi um prazer ajudá-lo! Qualquer dúvida, estamos disponíveis 24h. Tenha um ótimo dia! 👋"
    return {
        "resposta": resposta,
        "historico": [{"role": "assistant", "content": resposta}]
    }

def no_observabilidade(estado: EstadoAtendimento) -> dict:
    """Nó 7: Registra o atendimento no Langfuse."""
    try:
        trace_id = registrar_atendimento(
            nome="atendimento-multitech",
            usuario_id=estado.get("usuario_id", "anonimo"),
            mensagem=estado["mensagem"],
            resposta=estado["resposta"],
            intencao=estado["intencao"],
            tokens=estado.get("tokens_usados", 0),
            latencia_ms=estado.get("latencia_ms", 0),
            escalado=estado.get("escalado", False),
            fontes=estado.get("fontes", [])
        )
        print(f"[Langfuse] Trace registrado: {trace_id}")
    except Exception as e:
        print(f"[Langfuse] Erro ao registrar trace: {e}")
    return {}

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

    grafo.add_node("triagem", no_triagem)
    grafo.add_node("faq", no_faq)
    grafo.add_node("pos_venda", no_pos_venda)
    grafo.add_node("escalada", no_escalada)
    grafo.add_node("saudacao", no_saudacao)
    grafo.add_node("encerramento", no_encerramento)
    grafo.add_node("observabilidade", no_observabilidade)

    grafo.set_entry_point("triagem")

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

    # Todos os agentes passam pelo nó de observabilidade antes de terminar
    for no in ["faq", "pos_venda", "escalada", "saudacao", "encerramento"]:
        grafo.add_edge(no, "observabilidade")

    grafo.add_edge("observabilidade", END)

    return grafo.compile()

# ─────────────────────────────────────────
# INTERFACE DE ATENDIMENTO
# ─────────────────────────────────────────
app_grafo = criar_grafo()

def atender(mensagem: str, historico: list[dict] = None, usuario_id: str = "anonimo") -> dict:
    """Função principal de atendimento via grafo multi-agentes."""
    estado_inicial = {
        "mensagem": mensagem,
        "intencao": "",
        "historico": historico or [],
        "resposta": "",
        "protocolo": "",
        "escalado": False,
        "tentativas": 0,
        "tokens_usados": 0,
        "latencia_ms": 0,
        "fontes": [],
        "usuario_id": usuario_id
    }
    return app_grafo.invoke(estado_inicial)

if __name__ == "__main__":
    print("MultiTech — Sistema Multi-Agentes com Observabilidade\n")
    print("=" * 60)

    cenarios = [
        "Oi, boa tarde!",
        "Qual o prazo de entrega para Belo Horizonte?",
        "Quero devolver meu smartphone com defeito",
        "Obrigado, tchau!"
    ]

    historico = []
    for mensagem in cenarios:
        print(f"\nCliente: {mensagem}")
        resultado = atender(mensagem, historico, usuario_id="cliente-123")
        historico = resultado.get("historico", historico)
        print(f"Agente: {resultado['resposta'][:150]}...")
        print("-" * 60)