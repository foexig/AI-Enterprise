"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, clearToken, getToken } from "@/lib/api";
import type { Agent, ChatMessage, ChatSession, CurrentUser } from "@/lib/types";

// Dezente, deterministische Avatar-Farben pro Agent (keine Emojis, moderner Assistenten-Look)
const AGENT_COLORS = [
  "#c96442",
  "#7a6ee0",
  "#3f8f6d",
  "#4f8fbf",
  "#b5813c",
  "#b05575",
  "#8a68c9",
  "#5b8a72",
];

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash * 31 + value.charCodeAt(i)) | 0;
  }
  return Math.abs(hash);
}

const agentColor = (agent: Agent) => AGENT_COLORS[hashString(agent.slug) % AGENT_COLORS.length];
const initials = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 11) return "Guten Morgen";
  if (hour < 18) return "Guten Tag";
  return "Guten Abend";
}

const SUGGESTIONS = [
  "Was kannst du für mich tun?",
  "Fasse den letzten Vorfall zusammen",
  "Ich brauche Hilfe bei einer Aufgabe",
];

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

  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), 3500);
    return () => clearTimeout(timer);
  }, [error]);

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

  async function sendMessage(contentOverride?: string) {
    const content = (contentOverride ?? input).trim();
    if (!selectedAgent || !content || sending) return;
    setError(null);
    setInput("");
    setSending(true);

    // Noch keine Session? Dann automatisch eine anlegen (erste Nachricht
    // startet den Chat, ohne dass "+ Neuer Chat" geklickt werden muss).
    let session = activeSession;
    try {
      if (!session) {
        session = await apiFetch<ChatSession>(`/api/agents/${selectedAgent.id}/sessions`, {
          method: "POST",
        });
        setActiveSession(session);
        const list = await apiFetch<ChatSession[]>(`/api/agents/${selectedAgent.id}/sessions`);
        setSessions(list);
      }

      const sessionId = session.id;
      // Optimistisch die eigene Nachricht anzeigen
      setMessages((prev) => [
        ...prev,
        {
          id: -Date.now(),
          session_id: sessionId,
          role: "user",
          content,
          created_at: new Date().toISOString(),
        },
      ]);
      await apiFetch(`/api/sessions/${sessionId}/messages`, {
        method: "POST",
        body: JSON.stringify({ content }),
      });
      // Gesamte Historie vom Server übernehmen (echte IDs + AI-Antwort)
      const history = await apiFetch<ChatMessage[]>(`/api/sessions/${sessionId}/messages`);
      setMessages(history);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Senden fehlgeschlagen");
      // Optimistische Nachricht zurücknehmen; ggf. kaputte Auswahl korrigieren
      setMessages((prev) => prev.filter((m) => m.id > 0));
      if (session && session.id !== activeSession?.id) {
        setActiveSession(session);
      }
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

  const sessionLabel = (session: ChatSession) => {
    const date = new Date(session.last_activity_at);
    const today = new Date();
    const isToday = date.toDateString() === today.toDateString();
    return isToday
      ? date.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
      : date.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
  };

  return (
    <div className="app-shell">
      {/* ============ Sidebar ============ */}
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden />
          Enterprise AI
        </div>

        <div className="section-label">Agents</div>
        <nav>
          {agents.length === 0 && (
            <p className="sidebar-hint">Keine Agents für Sie freigegeben.</p>
          )}
          {agents.map((agent) => (
            <button
              key={agent.id}
              className={`agent-item ${selectedAgent?.id === agent.id ? "active" : ""}`}
              onClick={() => openAgent(agent)}
            >
              <span className="avatar" style={{ background: agentColor(agent) }}>
                {initials(agent.name)}
              </span>
              <span className="agent-item-text">
                <span className="name">{agent.name}</span>
                {agent.description && <span className="desc">{agent.description}</span>}
              </span>
            </button>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user-row">
            <span className="avatar user">{initials(me.name)}</span>
            <span className="user-meta">
              <span className="user-name">{me.name}</span>
              <span className="user-role">{me.is_admin ? "Administrator" : "Benutzer"}</span>
            </span>
          </div>
          <div className="footer-actions">
            {me.is_admin && (
              <button className="btn secondary small" onClick={() => router.push("/admin")}>
                Admin-Bereich
              </button>
            )}
            <button className="btn secondary small" onClick={logout}>
              Abmelden
            </button>
          </div>
        </div>
      </aside>

      {/* ============ Hauptbereich ============ */}
      <main className="main">
        {!selectedAgent ? (
          <div className="chat-area">
            <div className="empty-state">
              <div className="greeting">
                {greeting()}, {me.name.split(" ")[0]}
              </div>
              <p className="muted">
                Wählen Sie links einen Agent, um zu starten. Sie sehen ausschließlich die Agents,
                für die Sie freigeschaltet sind.
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="main-header">
              <div className="header-top">
                <h2>{selectedAgent.name}</h2>
                {sessions.length > 0 && (
                  <div className="session-bar">
                    {sessions.map((session) => (
                      <button
                        key={session.id}
                        className={`session-pill ${activeSession?.id === session.id ? "active" : ""}`}
                        onClick={() => openSession(session)}
                      >
                        {sessionLabel(session)}
                      </button>
                    ))}
                  </div>
                )}
                <button className="btn secondary small" onClick={newSession}>
                  + Neuer Chat
                </button>
              </div>
              {selectedAgent.description && (
                <p className="description">{selectedAgent.description}</p>
              )}
            </div>

            <div className="chat-area">
              <div className="messages">
                <div className="thread">
                  {messages.length === 0 && !sending && (
                    <div className="empty-state">
                      <div className="greeting small">
                        {greeting()}, {me.name.split(" ")[0]}
                      </div>
                      <p className="muted">Womit kann {selectedAgent.name} Ihnen helfen?</p>
                      <div className="suggestion-row">
                        {SUGGESTIONS.map((suggestion) => (
                          <button
                            key={suggestion}
                            className="suggestion-chip"
                            onClick={() => sendMessage(suggestion)}
                          >
                            {suggestion}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                  {messages.map((message) =>
                    message.role === "assistant" ? (
                      <div key={message.id} className="message assistant">
                        <span className="avatar" style={{ background: agentColor(selectedAgent) }}>
                          {initials(selectedAgent.name)}
                        </span>
                        <div className="msg-body">
                          <div className="msg-author">{selectedAgent.name}</div>
                          <div className="msg-content">{message.content}</div>
                        </div>
                      </div>
                    ) : (
                      <div key={message.id} className="message user">
                        {message.content}
                      </div>
                    )
                  )}
                  {sending && (
                    <div className="message assistant">
                      <span className="avatar" style={{ background: agentColor(selectedAgent) }}>
                        {initials(selectedAgent.name)}
                      </span>
                      <div className="msg-body">
                        <div className="msg-author">{selectedAgent.name}</div>
                        <div className="typing-dots" aria-label="Antwort wird generiert">
                          <span />
                          <span />
                          <span />
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="composer-wrap">
                <div className="composer">
                  <textarea
                    placeholder={`Nachricht an ${selectedAgent.name}...`}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    disabled={sending}
                    rows={1}
                  />
                  <button
                    className="send-btn"
                    onClick={() => sendMessage()}
                    disabled={sending || !input.trim()}
                    aria-label="Senden"
                  >
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
                      <path
                        d="M2.5 8L13.5 2.5L10.5 8L13.5 13.5L2.5 8Z"
                        fill="currentColor"
                        stroke="currentColor"
                        strokeWidth="1.2"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </button>
                </div>
                <p className="composer-hint">
                  Enter sendet · Shift+Enter für eine neue Zeile
                </p>
              </div>
            </div>
          </>
        )}
      </main>

      {/* Fehler als Toast unten rechts (Layout bleibt stabil) */}
      {error && (
        <div className="toast-stack">
          <div className="toast error">{error}</div>
        </div>
      )}
    </div>
  );
}
