import { useState } from "react";
import { api } from "../services/api";

export default function Login({ onAuth }) {
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "demo@example.com", password: "demo12345" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      const fn = mode === "login" ? api.login(form.email, form.password) : api.register(form.name, form.email, form.password);
      const res = await fn;
      onAuth(res.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-card">
      <h1>🌱 Smart Plant Care</h1>
      <p className="muted">Cloud-connected plant monitoring &amp; automated watering</p>
      <form onSubmit={submit}>
        {mode === "register" && (
          <input placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
        )}
        <input type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
        <input type="password" placeholder="Password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required minLength={8} />
        {error && <div className="error">{error}</div>}
        <button disabled={busy}>{busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}</button>
      </form>
      <button className="link" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Need an account? Register" : "Have an account? Log in"}
      </button>
      <p className="muted small">Demo credentials are pre-filled — run <code>python scripts/seed_demo.py</code> first.</p>
    </div>
  );
}
