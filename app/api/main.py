from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager
import time

from app.agents.orquestrador import atender
from app.observability.metrics import (
    registrar_atendimento_metrica,
    atendimentos_ativos,
    iniciar_servidor_metricas
)

# ─────────────────────────────────────────
# LIFESPAN — pré-carrega modelos pesados
# ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API] Pré-carregando modelos...")
    from app.rag.reranker import get_model
    get_model()
    print("[API] Modelos prontos.")
    yield
    print("[API] Encerrando...")

# ─────────────────────────────────────────
# APP FASTAPI
# ─────────────────────────────────────────
app = FastAPI(
    title="MultiTech — API de Atendimento",
    description="Sistema multi-agentes de atendimento ao cliente com RAG",
    version="1.0.0",
    lifespan=lifespan
)

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
    return {
        "status": "online",
        "servico": "MultiTech Atendimento",
        "versao": "1.0.0"
    }

@app.get("/health")
def health():
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

    atendimentos_ativos.inc()
    inicio = time.time()

    try:
        resultado = atender(
            mensagem=request.mensagem,
            historico=request.historico,
            usuario_id=request.usuario_id
        )

        latencia = int((time.time() - inicio) * 1000)

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
    return {
        "status": "online",
        "metricas_url": "http://localhost:8001/metrics",
        "grafana_url": "http://localhost:3000"
    }