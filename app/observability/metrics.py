from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# ─────────────────────────────────────────
# MÉTRICAS DO SISTEMA
# ─────────────────────────────────────────

# Contadores
atendimentos_total = Counter(
    "multitech_atendimentos_total",
    "Total de atendimentos realizados",
    ["intencao", "escalado"]
)

erros_total = Counter(
    "multitech_erros_total",
    "Total de erros no sistema",
    ["tipo", "agente"]
)

tokens_total = Counter(
    "multitech_tokens_total",
    "Total de tokens consumidos",
    ["agente"]
)

escaladas_total = Counter(
    "multitech_escaladas_total",
    "Total de escaladas para humano",
    ["motivo"]
)

# Histogramas (latência)
latencia_atendimento = Histogram(
    "multitech_latencia_atendimento_segundos",
    "Latência dos atendimentos em segundos",
    ["agente"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

latencia_rag = Histogram(
    "multitech_latencia_rag_segundos",
    "Latência do pipeline RAG em segundos",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

latencia_llm = Histogram(
    "multitech_latencia_llm_segundos",
    "Latência das chamadas ao LLM em segundos",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

# Gauges (valores instantâneos)
atendimentos_ativos = Gauge(
    "multitech_atendimentos_ativos",
    "Número de atendimentos em andamento"
)

# ─────────────────────────────────────────
# FUNÇÕES DE REGISTRO
# ─────────────────────────────────────────

def registrar_atendimento_metrica(
    intencao: str,
    escalado: bool,
    tokens: int,
    latencia_s: float,
    agente: str
) -> None:
    """Registra métricas de um atendimento completo."""
    atendimentos_total.labels(
        intencao=intencao,
        escalado=str(escalado)
    ).inc()

    tokens_total.labels(agente=agente).inc(tokens)

    latencia_atendimento.labels(agente=agente).observe(latencia_s)

    if escalado:
        escaladas_total.labels(motivo=intencao).inc()

def registrar_erro(tipo: str, agente: str) -> None:
    """Registra um erro no sistema."""
    erros_total.labels(tipo=tipo, agente=agente).inc()

def registrar_latencia_rag(latencia_s: float) -> None:
    """Registra latência do pipeline RAG."""
    latencia_rag.observe(latencia_s)

def registrar_latencia_llm(latencia_s: float) -> None:
    """Registra latência de chamada ao LLM."""
    latencia_llm.observe(latencia_s)

def iniciar_servidor_metricas(porta: int = 8001) -> None:
    """Inicia o servidor HTTP para o Prometheus coletar métricas."""
    start_http_server(porta)
    print(f"Métricas disponíveis em: http://localhost:{porta}/metrics")

if __name__ == "__main__":
    print("Iniciando servidor de métricas...")
    iniciar_servidor_metricas(8001)

    # Simula atendimentos para gerar métricas
    print("Simulando atendimentos...\n")

    cenarios = [
        ("Prazo_Entrega", False, 894, 9.19, "faq"),
        ("Produto_Defeito", True, 0, 1.2, "escalada"),
        ("Saudacao", False, 0, 0.3, "saudacao"),
        ("Devolver_Produto", True, 520, 4.5, "pos_venda"),
        ("Duvida_Geral", False, 780, 6.2, "faq"),
    ]

    for intencao, escalado, tokens, latencia, agente in cenarios:
        registrar_atendimento_metrica(intencao, escalado, tokens, latencia, agente)
        print(f"Registrado: {intencao} | Agente: {agente} | Escalado: {escalado}")

    print("\nMétricas geradas! Acesse: http://localhost:8001/metrics")
    print("Pressione Ctrl+C para encerrar.")

    while True:
        time.sleep(1)