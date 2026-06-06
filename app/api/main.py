## O que faz: cria o servidor FastAPI que vai expor o sistema multi-agentes como uma API REST — o ponto de entrada para qualquer canal (web, WhatsApp, app mobile).
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import time

from app.agents.orquestrador import atender
from app.observability.metrics import (
    registrar_atendimento_metrica,
    atendimentos_ativos,
    iniciar_servidor_metricas
)

# ─────────────────────────────────────────
# APP FASTAPI
# ─────────────────────────────────────────
app = FastAPI(
    title="MultiTech — API de Atendimento",
    description="Sistema multi-agentes de atendimento ao cliente com RAG",
    version="1.0.0"
)

# CORS — permite acesso de qualquer origem
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ─────────────────────────────────────────
# MODELOS
# ─────────────────────────────────────────
class MensagemRequest(BaseModel):
    mensagem: str
    usuario_id: Optional[str] = "anonimo"
    historico: Optional[list] = []

class AtendimentoResponse(BaseModel):
    resposta: str
    intencao: str
    escalado: bool
    protocolo: Optional[str] = None
    fontes: Optional[list] = []
    tokens_usados: int
    latencia_ms: int

# ─────────────────────────────────────────
# ROTAS
# ─────────────────────────────────────────
@app.get("/")
def health_check():
    """Health check da API."""
    return {
        "status": "online",
        "servico": "MultiTech Atendimento",
        "versao": "1.0.0"
    }

@app.get("/health")
def health():
    """Health check detalhado."""
    return {
        "status": "healthy",
        "componentes": {
            "api": "online",
            "rag": "online",
            "agentes": "online"
        }
    }

@app.post("/atender", response_model=AtendimentoResponse)
def endpoint_atender(request: MensagemRequest):
    """Endpoint principal de atendimento."""

    if not request.mensagem.strip():
        raise HTTPException(status_code=400, detail="Mensagem não pode ser vazia")

    # Registra atendimento ativo
    atendimentos_ativos.inc()
    inicio = time.time()

    try:
        # Chama o orquestrador
        resultado = atender(
            mensagem=request.mensagem,
            historico=request.historico,
            usuario_id=request.usuario_id
        )

        latencia = int((time.time() - inicio) * 1000)

        # Registra métricas
        registrar_atendimento_metrica(
            intencao=resultado.get("intencao", "Duvida_Geral"),
            escalado=resultado.get("escalado", False),
            tokens=resultado.get("tokens_usados", 0),
            latencia_s=latencia / 1000,
            agente=resultado.get("intencao", "faq").lower()
        )

        return AtendimentoResponse(
            resposta=resultado["resposta"],
            intencao=resultado.get("intencao", ""),
            escalado=resultado.get("escalado", False),
            protocolo=resultado.get("protocolo"),
            fontes=resultado.get("fontes", []),
            tokens_usados=resultado.get("tokens_usados", 0),
            latencia_ms=latencia
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        atendimentos_ativos.dec()

@app.get("/metricas/resumo")
def resumo_metricas():
    """Resumo das métricas do sistema."""
    return {
        "status": "online",
        "metricas_url": "http://localhost:8001/metrics",
        "grafana_url": "http://localhost:3000"
    }
    