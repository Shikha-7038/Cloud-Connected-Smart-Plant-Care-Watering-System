// Thin REST client for the Cloud Backend. Every call attaches the JWT (once logged in).
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authHeaders() {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  register: (name, email, password) => request("/api/auth/register", { method: "POST", body: JSON.stringify({ name, email, password }) }),
  login: (email, password) => request("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  listDevices: () => request("/api/devices"),
  createDevice: (body) => request("/api/devices", { method: "POST", body: JSON.stringify(body) }),
  getDevice: (id) => request(`/api/devices/${id}`),
  history: (id, hours = 24) => request(`/api/devices/${id}/history?hours=${hours}&limit=500`),
  wateringHistory: (id) => request(`/api/devices/${id}/watering-history`),
  setThreshold: (id, moisture_threshold) => request(`/api/devices/${id}/threshold`, { method: "PUT", body: JSON.stringify({ moisture_threshold }) }),
  setAuto: (id, auto_watering) => request(`/api/devices/${id}/auto`, { method: "PUT", body: JSON.stringify({ auto_watering }) }),
  waterNow: (id) => request(`/api/devices/${id}/water`, { method: "POST" }),
  analytics: (id, hours = 24) => request(`/api/devices/${id}/analytics?hours=${hours}`),
  alerts: (status) => request(`/api/alerts${status ? `?status=${status}` : ""}`),
  acknowledge: (id) => request(`/api/alerts/${id}/acknowledge`, { method: "PUT" }),
};
