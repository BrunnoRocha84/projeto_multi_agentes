import { useState, useRef, useEffect } from "react";
import axios from "axios";
import { Send, Bot, User, AlertCircle, CheckCircle, Clock, Zap, MessageSquare, TrendingUp } from "lucide-react";

const API_URL = "";

const SUGESTOES = [
  "Qual o prazo de entrega para Belo Horizonte?",
  "Como faço para devolver um produto com defeito?",
  "Quais formas de pagamento vocês aceitam?",
  "Meu smartphone está superaquecendo",
  "Preciso falar com um atendente humano",
];

export default function App() {
  const [mensagens, setMensagens] = useState([
    {
      role: "assistant",
      content: "Olá! Sou o assistente virtual da MultiTech. Como posso ajudá-lo hoje? 😊",
      intencao: "Saudacao",
      escalado: false,
      tokens: 0,
      latencia: 0,
      fontes: [],
    },
  ]);
  const [input, setInput] = useState("");
  const [carregando, setCarregando] = useState(false);
  const [historico, setHistorico] = useState([]);
  const [metricas, setMetricas] = useState({
    totalMensagens: 0,
    totalTokens: 0,
    latenciaMedia: 0,
    escaladas: 0,
    latencias: [],
  });
  const fimRef = useRef(null);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [mensagens]);

  const enviar = async (texto) => {
    const msg = texto || input.trim();
    if (!msg || carregando) return;

    const novaMsgUsuario = { role: "user", content: msg };
    setMensagens((prev) => [...prev, novaMsgUsuario]);
    setInput("");
    setCarregando(true);

    try {
      const res = await axios.post(`${API_URL}/atender`, {
        mensagem: msg,
        usuario_id: "usuario-frontend",
        historico,
      });

      const d = res.data;
      const novaMsgAgente = {
        role: "assistant",
        content: d.resposta,
        intencao: d.intencao,
        escalado: d.escalado,
        tokens: d.tokens_usados,
        latencia: d.latencia_ms,
        fontes: d.fontes || [],
        protocolo: d.protocolo,
      };

      setMensagens((prev) => [...prev, novaMsgAgente]);
      setHistorico((prev) => [
        ...prev,
        { role: "user", content: msg },
        { role: "assistant", content: d.resposta },
      ]);

      setMetricas((prev) => {
        const novasLatencias = [...prev.latencias, d.latencia_ms];
        const media = novasLatencias.reduce((a, b) => a + b, 0) / novasLatencias.length;
        return {
          totalMensagens: prev.totalMensagens + 1,
          totalTokens: prev.totalTokens + d.tokens_usados,
          latenciaMedia: Math.round(media),
          escaladas: prev.escaladas + (d.escalado ? 1 : 0),
          latencias: novasLatencias,
        };
      });
    } catch (err) {
      setMensagens((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.",
          erro: true,
        },
      ]);
    } finally {
      setCarregando(false);
    }
  };

  const limpar = () => {
    setMensagens([{
      role: "assistant",
      content: "Olá! Sou o assistente virtual da MultiTech. Como posso ajudá-lo hoje? 😊",
      intencao: "Saudacao",
      escalado: false,
      tokens: 0,
      latencia: 0,
      fontes: [],
    }]);
    setHistorico([]);
    setMetricas({ totalMensagens: 0, totalTokens: 0, latenciaMedia: 0, escaladas: 0, latencias: [] });
  };

  return (
    <div style={{ display: "flex", height: "100vh", fontFamily: "Arial, sans-serif", background: "#0f1117" }}>

      {/* CHAT */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", borderRight: "1px solid #2a2d3a" }}>

        {/* Header */}
        <div style={{ padding: "16px 24px", background: "#1a1d2e", borderBottom: "1px solid #2a2d3a", display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 40, height: 40, borderRadius: "50%", background: "linear-gradient(135deg, #4f46e5, #7c3aed)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Bot size={20} color="white" />
          </div>
          <div>
            <div style={{ color: "white", fontWeight: "bold", fontSize: 16 }}>MultiTech — Assistente Virtual</div>
            <div style={{ color: "#4ade80", fontSize: 12 }}>● Online</div>
          </div>
          <button onClick={limpar} style={{ marginLeft: "auto", background: "#2a2d3a", border: "none", color: "#9ca3af", padding: "6px 14px", borderRadius: 6, cursor: "pointer", fontSize: 13 }}>
            Nova conversa
          </button>
        </div>

        {/* Mensagens */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: 16 }}>
          {mensagens.map((msg, i) => (
            <div key={i} style={{ display: "flex", flexDirection: msg.role === "user" ? "row-reverse" : "row", gap: 10, alignItems: "flex-start" }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: msg.role === "user" ? "#4f46e5" : "#1e293b", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                {msg.role === "user" ? <User size={16} color="white" /> : <Bot size={16} color="#7c3aed" />}
              </div>
              <div style={{ maxWidth: "70%" }}>
                <div style={{
                  background: msg.role === "user" ? "#4f46e5" : msg.erro ? "#450a0a" : "#1e293b",
                  color: "white", padding: "12px 16px", borderRadius: msg.role === "user" ? "16px 4px 16px 16px" : "4px 16px 16px 16px",
                  fontSize: 14, lineHeight: 1.6, whiteSpace: "pre-wrap"
                }}>
                  {msg.content}
                </div>
                {msg.role === "assistant" && msg.intencao && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                    <span style={{ background: "#1e293b", color: "#818cf8", padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>
                      {msg.intencao}
                    </span>
                    {msg.escalado && (
                      <span style={{ background: "#450a0a", color: "#f87171", padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>
                        ⚠ Escalado
                      </span>
                    )}
                    {msg.protocolo && (
                      <span style={{ background: "#0c1a2e", color: "#60a5fa", padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>
                        {msg.protocolo}
                      </span>
                    )}
                    {msg.tokens > 0 && (
                      <span style={{ background: "#1e293b", color: "#6b7280", padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>
                        {msg.tokens} tokens · {msg.latencia}ms
                      </span>
                    )}
                    {msg.fontes?.length > 0 && (
                      <span style={{ background: "#1e293b", color: "#34d399", padding: "2px 8px", borderRadius: 12, fontSize: 11 }}>
                        📄 {msg.fontes.join(", ")}
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          {carregando && (
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#1e293b", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Bot size={16} color="#7c3aed" />
              </div>
              <div style={{ background: "#1e293b", padding: "12px 16px", borderRadius: "4px 16px 16px 16px" }}>
                <div style={{ display: "flex", gap: 4 }}>
                  {[0, 1, 2].map(i => (
                    <div key={i} style={{ width: 8, height: 8, borderRadius: "50%", background: "#7c3aed", animation: `pulse 1s ${i * 0.2}s infinite` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={fimRef} />
        </div>

        {/* Sugestões */}
        {mensagens.length <= 2 && (
          <div style={{ padding: "0 24px 12px", display: "flex", gap: 8, flexWrap: "wrap" }}>
            {SUGESTOES.map((s, i) => (
              <button key={i} onClick={() => enviar(s)} style={{ background: "#1e293b", border: "1px solid #2a2d3a", color: "#9ca3af", padding: "6px 12px", borderRadius: 16, cursor: "pointer", fontSize: 12, transition: "all 0.2s" }}
                onMouseEnter={e => e.target.style.borderColor = "#4f46e5"}
                onMouseLeave={e => e.target.style.borderColor = "#2a2d3a"}>
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{ padding: "16px 24px", background: "#1a1d2e", borderTop: "1px solid #2a2d3a", display: "flex", gap: 12 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && enviar()}
            placeholder="Digite sua mensagem..."
            style={{ flex: 1, background: "#0f1117", border: "1px solid #2a2d3a", color: "white", padding: "12px 16px", borderRadius: 8, fontSize: 14, outline: "none" }}
          />
          <button onClick={() => enviar()} disabled={carregando || !input.trim()} style={{ background: carregando || !input.trim() ? "#2a2d3a" : "#4f46e5", border: "none", color: "white", width: 44, height: 44, borderRadius: 8, cursor: carregando ? "not-allowed" : "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Send size={18} />
          </button>
        </div>
      </div>

      {/* PAINEL LATERAL */}
      <div style={{ width: 320, background: "#1a1d2e", display: "flex", flexDirection: "column", overflowY: "auto" }}>

        {/* Métricas da Sessão */}
        <div style={{ padding: "20px 20px 0" }}>
          <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: "bold", letterSpacing: 1, marginBottom: 12 }}>METRICAS DA SESSAO</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {[
              { icon: <MessageSquare size={16} />, label: "Mensagens", value: metricas.totalMensagens, color: "#818cf8" },
              { icon: <Zap size={16} />, label: "Tokens", value: metricas.totalTokens, color: "#34d399" },
              { icon: <Clock size={16} />, label: "Latencia media", value: metricas.latenciaMedia ? `${metricas.latenciaMedia}ms` : "—", color: "#fbbf24" },
              { icon: <AlertCircle size={16} />, label: "Escaladas", value: metricas.escaladas, color: "#f87171" },
            ].map((m, i) => (
              <div key={i} style={{ background: "#0f1117", borderRadius: 8, padding: "12px", border: "1px solid #2a2d3a" }}>
                <div style={{ color: m.color, marginBottom: 4 }}>{m.icon}</div>
                <div style={{ color: "white", fontSize: 20, fontWeight: "bold" }}>{m.value}</div>
                <div style={{ color: "#6b7280", fontSize: 11 }}>{m.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Historico de latencias */}
        <div style={{ padding: "20px" }}>
          <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: "bold", letterSpacing: 1, marginBottom: 12 }}>LATENCIA POR MENSAGEM</div>
          {metricas.latencias.length === 0 ? (
            <div style={{ color: "#6b7280", fontSize: 13, textAlign: "center", padding: "20px 0" }}>Aguardando mensagens...</div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {metricas.latencias.map((lat, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <div style={{ color: "#6b7280", fontSize: 11, width: 20 }}>#{i + 1}</div>
                  <div style={{ flex: 1, background: "#0f1117", borderRadius: 4, height: 6, overflow: "hidden" }}>
                    <div style={{ width: `${Math.min((lat / 15000) * 100, 100)}%`, height: "100%", background: lat > 10000 ? "#f87171" : lat > 5000 ? "#fbbf24" : "#34d399", borderRadius: 4 }} />
                  </div>
                  <div style={{ color: lat > 10000 ? "#f87171" : lat > 5000 ? "#fbbf24" : "#34d399", fontSize: 11, width: 55, textAlign: "right" }}>{lat}ms</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Links */}
        <div style={{ padding: "0 20px 20px", marginTop: "auto" }}>
          <div style={{ color: "#9ca3af", fontSize: 11, fontWeight: "bold", letterSpacing: 1, marginBottom: 12 }}>MONITORAMENTO</div>
          {[
            { label: "Grafana Dashboard", url: "http://localhost:3000", color: "#f97316" },
            { label: "Langfuse Traces", url: "https://cloud.langfuse.com", color: "#818cf8" },
            { label: "API Docs", url: "http://localhost:8000/docs", color: "#34d399" },
            { label: "Prometheus", url: "http://localhost:9090", color: "#fbbf24" },
          ].map((link, i) => (
            <a key={i} href={link.url} target="_blank" rel="noreferrer" style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 0", color: link.color, fontSize: 13, textDecoration: "none", borderBottom: "1px solid #2a2d3a" }}>
              <TrendingUp size={14} />
              {link.label}
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}