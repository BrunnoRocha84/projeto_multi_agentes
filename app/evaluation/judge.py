## O que faz: cria o avaliador automático que usa o Claude para julgar a qualidade das respostas geradas pelo sistema — fechando o loop de qualidade.
from anthropic import Anthropic
from app.config import ANTHROPIC_API_KEY
import json

client = Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT_JUDGE = """Você é um avaliador especializado em qualidade de atendimento ao cliente com IA.

Avalie a resposta do agente com base nos seguintes critérios:

1. GROUNDEDNESS (0-10): A resposta está fundamentada em fatos reais? Sem invenções?
2. RELEVANCIA (0-10): A resposta responde o que o cliente perguntou?
3. CLAREZA (0-10): A resposta é clara e fácil de entender?
4. COMPLETUDE (0-10): A resposta cobre todos os aspectos da pergunta?
5. TOM (0-10): O tom é adequado para atendimento ao cliente?

Retorne APENAS um JSON válido com essa estrutura:
{
  "groundedness": <0-10>,
  "relevancia": <0-10>,
  "clareza": <0-10>,
  "completude": <0-10>,
  "tom": <0-10>,
  "score_geral": <media dos scores>,
  "aprovado": <true se score_geral >= 7>,
  "problemas": ["lista de problemas encontrados"],
  "sugestoes": ["lista de sugestões de melhoria"]
}"""

def avaliar_resposta(
    pergunta: str,
    resposta: str,
    contexto: str = "",
    fontes: list = None
) -> dict:
    """Avalia a qualidade de uma resposta usando LLM-as-a-Judge."""

    prompt = f"""Avalie a seguinte interação de atendimento ao cliente:

PERGUNTA DO CLIENTE:
{pergunta}

CONTEXTO USADO (documentos recuperados):
{contexto or "Não fornecido"}

FONTES USADAS:
{', '.join(fontes or [])}

RESPOSTA DO AGENTE:
{resposta}

Avalie a qualidade desta resposta conforme os critérios estabelecidos."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": SYSTEM_PROMPT_JUDGE,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": prompt}]
    )

    texto = response.content[0].text.strip()

    # Remove markdown se presente
    if "```json" in texto:
        texto = texto.split("```json")[1].split("```")[0].strip()
    elif "```" in texto:
        texto = texto.split("```")[1].split("```")[0].strip()

    avaliacao = json.loads(texto)
    avaliacao["tokens_judge"] = response.usage.input_tokens + response.usage.output_tokens

    return avaliacao

def avaliar_lote(casos: list[dict]) -> dict:
    """Avalia um lote de casos e retorna métricas agregadas."""

    resultados = []
    aprovados = 0

    for caso in casos:
        avaliacao = avaliar_resposta(
            pergunta=caso["pergunta"],
            resposta=caso["resposta"],
            contexto=caso.get("contexto", ""),
            fontes=caso.get("fontes", [])
        )
        resultados.append({**caso, "avaliacao": avaliacao})
        if avaliacao.get("aprovado"):
            aprovados += 1

    scores = [r["avaliacao"]["score_geral"] for r in resultados]

    return {
        "total_casos": len(casos),
        "aprovados": aprovados,
        "reprovados": len(casos) - aprovados,
        "taxa_aprovacao": aprovados / len(casos) * 100,
        "score_medio": sum(scores) / len(scores),
        "score_minimo": min(scores),
        "score_maximo": max(scores),
        "resultados": resultados
    }

if __name__ == "__main__":
    print("LLM-as-a-Judge — MultiTech\n")
    print("=" * 60)

    casos = [
        {
            "pergunta": "Como faço para devolver um produto com defeito?",
            "resposta": """Conforme nossa política de devolução, você tem até 30 dias após a compra para devolver produtos com defeito. O produto deve estar em perfeito estado de conservação, com todos os acessórios originais e nota fiscal. Para iniciar o processo, entre em contato pelo chat ou e-mail suporte@multitech.com.br.""",
            "fontes": ["politica_devolucao", "faq_clientes"]
        },
        {
            "pergunta": "Qual o prazo de entrega para Belo Horizonte?",
            "resposta": """Para Belo Horizonte, sendo capital, o prazo de entrega é de 2 a 3 dias úteis. O código de rastreio será enviado por e-mail em até 24h após a compra.""",
            "fontes": ["faq_clientes"]
        },
        {
            "pergunta": "Meu smartphone está com defeito na câmera",
            "resposta": """Para resolver o problema da câmera, tente: reiniciar o dispositivo, limpar o cache do app de câmera e verificar atualizações de software. Se persistir, entre em contato para acionar a garantia pelo 0800 123 4567.""",
            "fontes": ["manual_smartphone", "faq_clientes"]
        }
    ]

    relatorio = avaliar_lote(casos)

    print(f"Total de casos: {relatorio['total_casos']}")
    print(f"Aprovados: {relatorio['aprovados']}")
    print(f"Taxa de aprovação: {relatorio['taxa_aprovacao']:.1f}%")
    print(f"Score médio: {relatorio['score_medio']:.2f}/10")
    print(f"Score mínimo: {relatorio['score_minimo']:.2f}/10")
    print(f"Score máximo: {relatorio['score_maximo']:.2f}/10")
    print("\nDetalhes por caso:")
    print("-" * 60)

    for r in relatorio["resultados"]:
        av = r["avaliacao"]
        status = "✅" if av["aprovado"] else "❌"
        print(f"{status} {r['pergunta'][:50]}...")
        print(f"   Score: {av['score_geral']:.1f} | Groundedness: {av['groundedness']} | Relevância: {av['relevancia']}")
        if av.get("problemas"):
            print(f"   Problemas: {av['problemas']}")
        print()