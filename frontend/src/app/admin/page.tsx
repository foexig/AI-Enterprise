"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiFetch, getToken } from "@/lib/api";
import type { AdminAgent, AdminRole, AdminUser, CurrentUser } from "@/lib/types";

// Vorschläge für die Modellauswahl; der gültige Wert kommt immer aus der Agent-Konfiguration
const MODEL_SUGGESTIONS = [
  "eu.anthropic.claude-3-5-sonnet-20241022-v2:0",
  "eu.anthropic.claude-3-5-haiku-20241022-v2:0",
  "eu.amazon.titan-text-express-v1",
  "eu.meta.llama3-1-70b-instruct-v1:0",
];

type Tab = "agents" | "users" | "roles";

export default function AdminPage() {
  const router = useRouter();
  const [me, setMe] = useState<CurrentUser | null>(null);
  const [tab, setTab] = useState<Tab>("agents");
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [agents, setAgents] = useState<AdminAgent[]>([]);

  // Agents-Tab: Auswahl über Dropdown
  const [selectedAgent, setSelectedAgent] = useState<AdminAgent | null>(null);
  const [showCreateAgent, setShowCreateAgent] = useState(false);

  // Rollen-Tab: Lösch-Bestätigung
  const [roleToDelete, setRoleToDelete] = useState<AdminRole | null>(null);
  const [deleteBusy, setDeleteBusy] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [u, r, a] = await Promise.all([
      apiFetch<AdminUser[]>("/api/admin/users"),
      apiFetch<AdminRole[]>("/api/admin/roles"),
      apiFetch<AdminAgent[]>("/api/admin/agents"),
    ]);
    setUsers(u);
    setRoles(r);
    setAgents(a);
    setSelectedAgent((current) => {
      if (!current) return null;
      const fresh = a.find((agent) => agent.id === current.id);
      return fresh ?? null;
    });
  }, []);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    (async () => {
      try {
        const user = await apiFetch<CurrentUser>("/api/auth/me");
        if (!user.is_admin) {
          router.replace("/");
          return;
        }
        setMe(user);
        await refresh();
      } catch {
        // apiFetch leitet bei 401 weiter
      }
    })();
  }, [router, refresh]);

  function flash(message: string) {
    setNotice(message);
    setError(null);
    setTimeout(() => setNotice(null), 3500);
  }

  function handleFailure(err: unknown, context: string) {
    setError(`${context}: ${err instanceof Error ? err.message : "unbekannter Fehler"}`);
  }

  // ---------- Agents ----------
  async function updateAgent(agent: AdminAgent, patch: Partial<AdminAgent>) {
    try {
      await apiFetch<AdminAgent>(`/api/admin/agents/${agent.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      flash(`Agent "${agent.name}" gespeichert.`);
      await refresh();
    } catch (err) {
      handleFailure(err, "Speichern fehlgeschlagen");
    }
  }

  async function updateAgentRoles(agent: AdminAgent, roleIds: number[]) {
    try {
      await apiFetch(`/api/admin/agents/${agent.id}/roles`, {
        method: "POST",
        body: JSON.stringify({ role_ids: roleIds }),
      });
      flash(`Rollen von "${agent.name}" aktualisiert.`);
      await refresh();
    } catch (err) {
      handleFailure(err, "Rollen-Speichern fehlgeschlagen");
    }
  }

  async function createAgent(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const created = await apiFetch<AdminAgent>("/api/admin/agents", {
        method: "POST",
        body: JSON.stringify({
          name: data.get("name"),
          slug: data.get("slug"),
          description: data.get("description") || "",
          system_prompt: data.get("system_prompt") || "",
          model_id: data.get("model_id"),
          role_ids: data.getAll("role_ids").map(Number),
        }),
      });
      form.reset();
      setShowCreateAgent(false);
      flash("Agent angelegt.");
      await refresh();
      setSelectedAgent(created);
    } catch (err) {
      handleFailure(err, "Anlegen fehlgeschlagen");
    }
  }

  // ---------- Users ----------
  async function createUser(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await apiFetch("/api/admin/users", {
        method: "POST",
        body: JSON.stringify({
          email: data.get("email"),
          password: data.get("password"),
          name: data.get("name"),
          is_admin: data.get("is_admin") === "on",
          role_ids: data.getAll("role_ids").map(Number),
        }),
      });
      form.reset();
      flash("Benutzer angelegt.");
      await refresh();
    } catch (err) {
      handleFailure(err, "Anlegen fehlgeschlagen");
    }
  }

  async function updateUser(user: AdminUser, patch: Record<string, unknown>) {
    try {
      await apiFetch(`/api/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      });
      flash(`Benutzer "${user.name}" gespeichert.`);
      await refresh();
    } catch (err) {
      handleFailure(err, "Speichern fehlgeschlagen");
    }
  }

  async function updateUserRoles(user: AdminUser, roleIds: number[]) {
    try {
      await apiFetch(`/api/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify({ role_ids: roleIds }),
      });
      flash(`Rollen von "${user.name}" aktualisiert.`);
      await refresh();
    } catch (err) {
      handleFailure(err, "Rollen-Speichern fehlgeschlagen");
    }
  }

  // ---------- Roles ----------
  async function createRole(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      await apiFetch("/api/admin/roles", {
        method: "POST",
        body: JSON.stringify({ name: data.get("name") }),
      });
      form.reset();
      flash("Rolle angelegt.");
      await refresh();
    } catch (err) {
      handleFailure(err, "Anlegen fehlgeschlagen");
    }
  }

  async function confirmDeleteRole() {
    if (!roleToDelete || deleteBusy) return;
    setDeleteBusy(true);
    try {
      await apiFetch(`/api/admin/roles/${roleToDelete.id}`, { method: "DELETE" });
      flash(`Rolle "${roleToDelete.name}" gelöscht.`);
      setRoleToDelete(null);
      await refresh();
    } catch (err) {
      handleFailure(err, "Löschen fehlgeschlagen");
      setRoleToDelete(null);
    } finally {
      setDeleteBusy(false);
    }
  }

  if (!me) return <div className="login-page"><p className="muted">Lade...</p></div>;

  return (
    <div className="admin-page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <h1>Admin-Bereich</h1>
        <button className="btn secondary small" onClick={() => router.push("/")}>← Zurück zum Chat</button>
      </div>

      <div className="admin-tabs">
        {(["agents", "users", "roles"] as Tab[]).map((t) => (
          <button key={t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>
            {t === "agents" ? "Agents" : t === "users" ? "Benutzer" : "Rollen"}
          </button>
        ))}
      </div>

      {error && <div className="error-box">{error}</div>}
      {notice && <div className="success-box">{notice}</div>}

      {/* ============ Agents ============ */}
      {tab === "agents" && (
        <>
          <div className="card">
            <div className="toolbar">
              <select
                value={selectedAgent?.id ?? ""}
                onChange={(e) =>
                  setSelectedAgent(
                    e.target.value === "" ? null : agents.find((a) => a.id === Number(e.target.value)) ?? null
                  )
                }
              >
                <option value="">Agent auswählen...</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                    {agent.is_active ? "" : " (deaktiviert)"}
                  </option>
                ))}
              </select>
              <button
                className="btn secondary"
                onClick={() => setShowCreateAgent((v) => !v)}
              >
                {showCreateAgent ? "Abbrechen" : "+ Neuen Agent anlegen"}
              </button>
            </div>
          </div>

          {showCreateAgent && (
            <div className="card">
              <h3>Neuen Agent anlegen</h3>
              <form onSubmit={createAgent}>
                <div className="form-grid">
                  <div className="field">
                    <label>Name</label>
                    <input name="name" required placeholder="z.B. Buchhaltung" />
                  </div>
                  <div className="field">
                    <label>Slug</label>
                    <input name="slug" required pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="buchhaltung" />
                  </div>
                  <div className="field">
                    <label>Modell</label>
                    <input name="model_id" required defaultValue={MODEL_SUGGESTIONS[0]} list="model-suggestions" />
                  </div>
                </div>
                <datalist id="model-suggestions">
                  {MODEL_SUGGESTIONS.map((m) => (
                    <option key={m} value={m} />
                  ))}
                </datalist>
                <div className="field">
                  <label>Beschreibung</label>
                  <input name="description" placeholder="Wofür ist dieser Agent da?" />
                </div>
                <div className="field">
                  <label>System Prompt</label>
                  <textarea name="system_prompt" placeholder="Du bist der interne ...-Assistent..." />
                </div>
                <div>
                  <label style={{ fontWeight: 600, fontSize: 13 }}>Rollen mit Zugriff:</label>
                  {roles.map((role) => (
                    <label className="checkbox-row" key={role.id}>
                      <input type="checkbox" name="role_ids" value={role.id} />
                      {role.name}
                    </label>
                  ))}
                </div>
                <button className="btn" type="submit" style={{ marginTop: 12 }}>
                  Agent anlegen
                </button>
              </form>
            </div>
          )}

          {selectedAgent && (
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <h3>
                  {selectedAgent.name} <span className="muted">({selectedAgent.slug})</span>
                </h3>
                <span className={`badge ${selectedAgent.is_active ? "on" : "off"}`}>
                  {selectedAgent.is_active ? "aktiv" : "deaktiviert"}
                </span>
              </div>

              <div className="form-grid">
                <div className="field">
                  <label>Name</label>
                  <input
                    defaultValue={selectedAgent.name}
                    onBlur={(e) =>
                      e.target.value !== selectedAgent.name && updateAgent(selectedAgent, { name: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label>Modell (Bedrock Model-ID)</label>
                  <input
                    defaultValue={selectedAgent.model_id}
                    list="model-suggestions"
                    onBlur={(e) =>
                      e.target.value !== selectedAgent.model_id &&
                      updateAgent(selectedAgent, { model_id: e.target.value })
                    }
                  />
                </div>
                <div className="field">
                  <label>Beschreibung</label>
                  <input
                    defaultValue={selectedAgent.description}
                    onBlur={(e) =>
                      e.target.value !== selectedAgent.description &&
                      updateAgent(selectedAgent, { description: e.target.value })
                    }
                  />
                </div>
              </div>

              <div className="field">
                <label>System Prompt</label>
                <textarea
                  defaultValue={selectedAgent.system_prompt}
                  onBlur={(e) =>
                    e.target.value !== selectedAgent.system_prompt &&
                    updateAgent(selectedAgent, { system_prompt: e.target.value })
                  }
                />
              </div>

              <div style={{ margin: "10px 0" }}>
                <label style={{ fontWeight: 600, fontSize: 13 }}>Rollen mit Zugriff:</label>
                {roles.map((role) => (
                  <label className="checkbox-row" key={role.id}>
                    <input
                      type="checkbox"
                      checked={selectedAgent.roles.includes(role.name)}
                      onChange={(e) => {
                        const current = roles
                          .filter((r) => selectedAgent.roles.includes(r.name))
                          .map((r) => r.id);
                        const next = e.target.checked
                          ? [...current, role.id]
                          : current.filter((id) => id !== role.id);
                        updateAgentRoles(selectedAgent, next);
                      }}
                    />
                    {role.name}
                  </label>
                ))}
                {roles.length === 0 && <p className="muted">Noch keine Rollen vorhanden.</p>}
              </div>

              <div className="actions-row">
                <button
                  className={`btn small ${selectedAgent.is_active ? "danger" : ""}`}
                  onClick={() => updateAgent(selectedAgent, { is_active: !selectedAgent.is_active })}
                >
                  {selectedAgent.is_active ? "Agent deaktivieren" : "Agent aktivieren"}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* ============ Users ============ */}
      {tab === "users" && (
        <>
          <div className="card">
            <h3>Benutzer</h3>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>E-Mail</th>
                  <th>Rollen</th>
                  <th>Status</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id}>
                    <td>
                      {user.name}
                      {user.is_admin && <span className="badge on">Admin</span>}
                    </td>
                    <td>{user.email}</td>
                    <td style={{ minWidth: 180 }}>
                      {roles.map((role) => (
                        <label className="checkbox-row" key={role.id}>
                          <input
                            type="checkbox"
                            checked={user.roles.includes(role.name)}
                            onChange={(e) => {
                              const current = roles
                                .filter((r) => user.roles.includes(r.name))
                                .map((r) => r.id);
                              const next = e.target.checked
                                ? [...current, role.id]
                                : current.filter((id) => id !== role.id);
                              updateUserRoles(user, next);
                            }}
                          />
                          {role.name}
                        </label>
                      ))}
                    </td>
                    <td>
                      <span className={`badge ${user.is_active ? "on" : "off"}`}>
                        {user.is_active ? "aktiv" : "deaktiviert"}
                      </span>
                    </td>
                    <td>
                      <button
                        className="btn small secondary"
                        onClick={() => updateUser(user, { is_active: !user.is_active })}
                        disabled={user.id === me.id}
                      >
                        {user.is_active ? "Deaktivieren" : "Aktivieren"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card">
            <h3>Neuen Benutzer anlegen</h3>
            <form onSubmit={createUser}>
              <div className="form-grid">
                <div className="field">
                  <label>Name</label>
                  <input name="name" required />
                </div>
                <div className="field">
                  <label>E-Mail</label>
                  <input name="email" type="email" required />
                </div>
                <div className="field">
                  <label>Passwort (min. 8 Zeichen)</label>
                  <input name="password" type="password" minLength={8} required />
                </div>
              </div>
              <div>
                <label style={{ fontWeight: 600, fontSize: 13 }}>Rollen:</label>
                {roles.map((role) => (
                  <label className="checkbox-row" key={role.id}>
                    <input type="checkbox" name="role_ids" value={role.id} />
                    {role.name}
                  </label>
                ))}
              </div>
              <label className="checkbox-row" style={{ marginTop: 8 }}>
                <input type="checkbox" name="is_admin" />
                Plattform-Admin
              </label>
              <button className="btn" type="submit" style={{ marginTop: 12 }}>
                Benutzer anlegen
              </button>
            </form>
          </div>
        </>
      )}

      {/* ============ Roles ============ */}
      {tab === "roles" && (
        <>
          <div className="card">
            <h3>Rollen</h3>
            <table>
              <thead>
                <tr>
                  <th>Rolle</th>
                  <th>Benutzer</th>
                  <th>Agents mit Zugriff</th>
                  <th>Aktionen</th>
                </tr>
              </thead>
              <tbody>
                {roles.map((role) => (
                  <tr key={role.id}>
                    <td>{role.name}</td>
                    <td>{role.user_count}</td>
                    <td>{role.agent_count}</td>
                    <td>
                      <button className="btn small danger" onClick={() => setRoleToDelete(role)}>
                        Löschen
                      </button>
                    </td>
                  </tr>
                ))}
                {roles.length === 0 && (
                  <tr>
                    <td colSpan={4} className="muted">
                    Noch keine Rollen vorhanden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div className="card">
            <h3>Neue Rolle anlegen</h3>
            <form onSubmit={createRole} style={{ display: "flex", gap: 10 }}>
              <input name="name" required placeholder="z.B. Vertrieb" />
              <button className="btn" type="submit">
                Anlegen
              </button>
            </form>
          </div>
        </>
      )}

      {/* ============ Lösch-Bestätigung (Rollen) ============ */}
      {roleToDelete && (
        <div className="modal-backdrop" onClick={() => !deleteBusy && setRoleToDelete(null)}>
          <div className="card modal" onClick={(e) => e.stopPropagation()}>
            <h3>Rolle löschen?</h3>
            <p style={{ marginBottom: 8 }}>
              Möchten Sie die Rolle <b>{roleToDelete.name}</b> wirklich löschen?
            </p>
            <p className="muted" style={{ marginBottom: 16 }}>
              Diese Rolle haben aktuell <b>{roleToDelete.user_count}</b>{" "}
              {roleToDelete.user_count === 1 ? "Benutzer" : "Benutzer"}. Sie gewährt Zugriff auf{" "}
              <b>{roleToDelete.agent_count}</b> {roleToDelete.agent_count === 1 ? "Agent" : "Agents"}.
              Diese Zuordnungen werden mit entfernt - betroffene Benutzer verlieren dann den Zugriff
              auf die zugehörigen Agents.
            </p>
            <div className="actions-row">
              <button className="btn danger" onClick={confirmDeleteRole} disabled={deleteBusy}>
                {deleteBusy ? "Lösche..." : "Ja, Rolle löschen"}
              </button>
              <button className="btn secondary" onClick={() => setRoleToDelete(null)} disabled={deleteBusy}>
                Abbrechen
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
