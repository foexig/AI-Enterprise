"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearToken, getToken } from "@/lib/api";
import type { Agent, ChatMessage, ChatSession, CurrentUser } from "@/lib/types";

// dezente Icons pro Agent-Slug (wie in der Spezifikation skizziert)
const AGENT_ICONS: Record<string, string> = {
  "it-support": "🖥",
  softwareentwicklung: "⌨",
  logistik: "📦",
  kundenservice: "👥",
  einkauf: "💰",
  buchhaltung: "🧾",
};
const DEFAULT_ICON = "🤖";
const iconFor = (agent: Agent) => AGENT_ICONS[agent.slug] ?? DEFAULT_ICON;

export default function ChatPage() {
  const router = useRouter();
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const user = await apiFetch<CurrentUser>("/api/auth/me");
        setMe(user);
        const list = await apiFetch<Agent[]>("/api/agents");
        setAgents(list);
      } catch {
        // apiFetch leitet bei 401 bereits zu /login weiter
      }
    })();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const openAgent = useCallback(async (agent: Agent) => {
    setSelectedAgent(agent);
    setActiveSession(null);
    setMessages([]);
    try {
      const list = await apiFetch<ChatSession[]>(`/api/agents/${agent.id}/sessions`);
      setSessions(list);
      if (list.length > 0) {
        const session = list[0];
        setActiveSession(session);
        const history = await apiFetch<ChatMessage[]>(`/api/sessions/${session.id}/messages`);
        setMessages(history);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Laden");
    }
  }, []);

  async function newSession() {
    if (!selectedAgent) return;
    setError(null);
    try {
      const session = await apiFetch<ChatSession>(`/api/agents/${selectedAgent.id}/sessions`, {
        method: "POST",
      });
      setActiveSession(session);
      setMessages([]);
      const list = await apiFetch<ChatSession[]>(`/api/agents/${selectedAgent.id}/sessions`);
      setSessions(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Erstellen der Session");
    }
  }

  async function openSession(session: ChatSession) {
    if (!selectedAgent) return;
    setError(null);
    try {
      const history = await apiFetch<ChatMessage[]>(`/api/sessions/${session.id}/messages`);
      setActiveSession(session);
      setMessages(history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Laden der Session");
    }
  }

  async function sendMessage() {
    if (!selectedAgent || !activeSession || !input.trim() || sending) return;
    const content = input.trim();
    setInput("");
    setSending(true);
    setError(null);
    // Optimistisch die eigene Nachricht anzeigen
    setMessages((prev) => [
      ...prev,
      {
        id: -Date.now(),
        session_id: activeSession.id,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      },
    ]);
    try {
      const response = await apiFetch<{
        message: ChatMessage;
        input_tokens: number;
        output_tokens: number;
      }>(`/api/sessions/${activeSession.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      // echte Nutzer-Nachricht vom Server + AI-Antwort übernehmen
      const history = await apiFetch<ChatMessage[]>(`/api/sessions/${activeSession.id}/messages`);
      setMessages(history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Senden fehlgeschlagen");
      // Bei 403 (z.B. abgelaufene Session) State zurücksetzen
      setMessages((prev) => prev.filter((m) => m.id > 0));
    } finally {
      setSending(false);
    }
  }

  function logout() {
    clearToken();
    router.push("/login");
  }

  if (!me) {
    return <div className="login-page"><p className="muted">Lade...</p></div>;
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">Enterprise AI</div>
        <div className="section-label">Agents</div>
        <nav>
          {agents.length === 0 && (
            <p style={{ padding: "0 10px", fontSize: 13, color: "#98a2b3" }}>
              Keine Agents für Sie freigegeben.
            </p>
          )}
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={`agent-item ${selectedAgent?.id === agent.id ? "active" : ""}`}
              onClick={() => openAgent(agent)}
            >
              <span className="icon">{iconFor(agent)}</span>
              <span>{agent.name}</span>
            </button>
          ))}
        </nav>
        <div className="footer">
          <span>
            {me.name}
            {me.is_admin && " (Admin)"}
          </span>
          {me.is_admin && (
            <button className="btn secondary small" onClick={() => router.push("/admin")}>
              Admin-Bereich
            </button>
          )}
          <button className="btn secondary small" onClick={logout}>
            Abmelden
          </button>
        </div>
      </aside>

      <main className="main">
        {!selectedAgent ? (
          <div className="chat-area">
            <div className="empty-state">
              <div className="big-icon">🤖</div>
              <h2>Wählen Sie einen Agent</h2>
              <p className="muted">
                Sie sehen ausschließlich die Agents, für die Sie freigeschaltet sind.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="main-header">
              <h2>{selectedAgent.name}</h2>
              <p className="description">{selectedAgent.description}</p>
            </div>

            <div className="session-bar">
              {sessions.map((session) => (
                <button
                  key={session.id}
                  className={`session-pill ${activeSession?.id === session.id ? "active" : ""}`}
                  onClick={() => openSession(session)}
                >
                  #{session.id} · {new Date(session.last_activity_at).toLocaleString("de-DE")}
                </button>
              ))}
              <button className="btn secondary small" onClick={newSession}>
                + Neuer Chat
              </button>
            </div>

            {error && <div className="error-box" style={{ margin: "12px 24px 0" }}>{error}</div>}

            <div className="chat-area">
              <div className="messages">
                {messages.length === 0 && (
                  <div className="empty-state">
                    <p>Stellen Sie Ihre erste Frage an {selectedAgent.name}.</p>
                  </div>
                )}
                {messages.map((message) => (
                  <div key={message.id} className={`message ${message.role}`}>
                    {message.content}
                  </div>
                ))}
                {sending && <div className="message assistant muted">Antwort wird generiert...</div>}
                <div ref={messagesEndRef} />
              </div>

              <div className="composer">
                <textarea
                  placeholder="Nachricht eingeben..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      sendMessage();
                    }
                  }}
                  disabled={!activeSession || sending}
                />
                <button className="btn" onClick={sendMessage} disabled={!activeSession || sending || !input.trim()}>
                  Senden
                </button>
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
