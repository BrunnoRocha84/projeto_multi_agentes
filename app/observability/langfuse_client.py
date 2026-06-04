from langfuse import Langfuse
from app.config import LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
from datetime import datetime
import time

# Cliente Langfuse v4
langfuse = Langfuse(
    public_key=LANGFUSE_PUBLIC_KEY,
    secret_key=LANGFUSE_SECRET_KEY,
    host=LANGFUSE_HOST
)

def registrar_atendimento(
    nome: str,
    usuario_id: str,
    mensagem: str,
    resposta: str,
    intencao: str,
    tokens: int = 0,
    latencia_ms: int = 0,
    escalado: bool = False,
    fontes: list = None
) -> str:
    """Registra um atendimento completo no Langfuse."""

    trace_id = langfuse.create_trace_id()

    with langfuse.start_as_current_observation(
        name=nome,
        as_type="span",
        input={"mensagem": mensagem},
        metadata={
            "timestamp": datetime.now().isoformat(),
            "usuario_id": usuario_id,
            "sistema": "multitech-atendimento",
            "trace_id": trace_id
        }
    ):
        # Span de triagem
        with langfuse.start_as_current_observation(
            name="triagem",
            as_type="span",
            input={"mensagem": mensagem},
            metadata={"intencao": intencao}
        ):
            pass

        # Geração do LLM
        with langfuse.start_as_current_observation(
            name="llm-resposta",
            as_type="generation",
            model="claude-sonnet-4-5",
            input=mensagem,
            output=resposta,
            usage_details={
                "input": tokens // 2,
                "output": tokens // 2,
                "total": tokens
            },
            metadata={
                "latencia_ms": latencia_ms,
                "fontes": fontes or [],
                "escalado": escalado
            }
        ):
            pass

    langfuse.flush()
    return trace_id

def medir_tempo(func):
    """Decorator para medir latência de funções."""
    def wrapper(*args, **kwargs):
        inicio = time.time()
        resultado = func(*args, **kwargs)
        fim = time.time()
        latencia = int((fim - inicio) * 1000)
        if isinstance(resultado, dict):
            resultado["latencia_ms"] = latencia
        return resultado
    return wrapper

if __name__ == "__main__":
    print("Testando conexão com Langfuse v4...")

    trace_id = registrar_atendimento(
        nome="teste-conexao",
        usuario_id="usuario-teste",
        mensagem="Como faço para devolver um produto?",
        resposta="Conforme nossa política, o prazo é de 30 dias.",
        intencao="Devolver_Produto",
        tokens=850,
        latencia_ms=1200,
        escalado=False,
        fontes=["politica_devolucao", "faq_clientes"]
    )

    print(f"Trace registrado: {trace_id}")
    print(f"Acesse: {LANGFUSE_HOST}")