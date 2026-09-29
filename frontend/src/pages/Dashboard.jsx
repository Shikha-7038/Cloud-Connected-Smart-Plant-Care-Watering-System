import { useEffect, useState } from "react";
import AlertsPanel from "../components/AlertsPanel";
import DeviceCard from "../components/DeviceCard";
import HistoryChart from "../components/HistoryChart";
import StatCard from "../components/StatCard";
import { api } from "../services/api";

const HOURS = 24;

export default function Dashboard({ onLogout }) {
  const [devices, setDevices] = useState([]);
  const [selected, setSelected] = useState(null);
  const [history, setHistory] = useState([]);
  const [watering, setWatering] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [thresholdDraft, setThresholdDraft] = useState("");
  const [error, setError] = useState("");

  const device = devices.find((d) => d.device_id === selected);

  async function refreshDevices() {
    try {
      const list = await api.listDevices();
      setDevices(list);
      if (!selected && list.length) setSelected(list[0].device_id);
    } catch (e) { setError(e.message); }
  }

  async function refreshDetail(id) {
    const [h, w, a, al] = await Promise.all([
      api.history(id, HOURS), api.wateringHistory(id), api.analytics(id, HOURS), api.alerts(),
    ]);
    setHistory(h); setWatering(w); setAnalytics(a); setAlerts(al.filter((x) => x.device_id === id || true));
  }

  useEffect(() => { refreshDevices(); const t = setInterval(refreshDevices, 5000); return () => clearInterval(t); }, []);
  useEffect(() => {
    if (!selected) return;
    setThresholdDraft(device?.moisture_threshold ?? "");
    refreshDetail(selected);
    const t = setInterval(() => refreshDetail(selected), 5000);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected]);

  async function water() {
    try { await api.waterNow(selected); refreshDetail(selected); } catch (e) { setError(e.message); }
  }
  async function toggleAuto() {
    await api.setAuto(selected, !device.auto_watering); refreshDevices();
  }
  async function saveThreshold() {
    await api.setThreshold(selected, Number(thresholdDraft)); refreshDevices();
  }
  async function ack(id) {
    await api.acknowledge(id); refreshDetail(selected);
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h2>🌱 My Plants</h2>
        {devices.map((d) => <DeviceCard key={d.device_id} device={d} active={d.device_id === selected} onSelect={setSelected} />)}
        <button className="logout-btn" onClick={onLogout}>Log out</button>
      </aside>
      <main className="main">
        {error && <div className="error">{error}</div>}
        {!device ? <p className="muted">Select a plant, or add one via the API (POST /api/devices).</p> : (
          <>
            <header className="main-header">
              <div>
                <h1>{device.plant_name}</h1>
                <span className="muted">{device.device_id} · {device.location || "—"} · {device.plant_type}</span>
              </div>
              <div className="controls">
                <button onClick={water} disabled={device.pump_on}>💧 Water Now</button>
                <label className="toggle">
                  <input type="checkbox" checked={device.auto_watering} onChange={toggleAuto} /> Auto-water
                </label>
              </div>
            </header>

            <section className="stat-grid">
              <StatCard icon="💧" label="Soil Moisture" value={device.latest?.soil_moisture} unit="%" warn={device.plant_health !== "Healthy"} />
              <StatCard icon="🌡️" label="Temperature" value={device.latest?.temperature} unit="°C" />
              <StatCard icon="💦" label="Humidity" value={device.latest?.humidity} unit="%" />
              <StatCard icon="☀️" label="Light" value={device.latest?.light_level} unit="%" />
              <StatCard icon="⚙️" label="Pump Status" value={device.pump_on ? "ON" : "OFF"} unit="" warn={device.pump_on} />
              <StatCard icon="🩺" label="Plant Status" value={device.plant_health} unit="" />
            </section>

            <section className="threshold-row">
              <label>Moisture threshold %
                <input type="number" min={0} max={100} value={thresholdDraft} onChange={(e) => setThresholdDraft(e.target.value)} />
              </label>
              <button onClick={saveThreshold}>Save</button>
              <span className="muted small">Target (stop watering): {device.target_moisture}% · Last watered: {device.last_watered_at ? new Date(device.last_watered_at).toLocaleString() : "never"}</span>
            </section>

            <section className="chart-grid">
              <HistoryChart title="Soil Moisture Over Time" data={history} lines={[{ key: "soil_moisture", name: "Soil %", color: "#2ecc71" }]} />
              <HistoryChart title="Temperature Over Time" data={history} lines={[{ key: "temperature", name: "°C", color: "#e67e22" }]} />
              <HistoryChart title="Humidity Over Time" data={history} lines={[{ key: "humidity", name: "Humidity %", color: "#3498db" }]} />
            </section>

            <section className="two-col">
              <div className="chart-card">
                <h3>Watering History</h3>
                <table>
                  <thead><tr><th>When</th><th>Trigger</th><th>Before</th><th>After</th><th>Duration</th></tr></thead>
                  <tbody>
                    {watering.slice(0, 10).map((w) => (
                      <tr key={w.event_id}>
                        <td>{new Date(w.timestamp).toLocaleString()}</td>
                        <td>{w.trigger_type}</td>
                        <td>{w.moisture_before}%</td>
                        <td>{w.moisture_after ?? "…"}%</td>
                        <td>{w.duration ? `${w.duration}s` : "…"}</td>
                      </tr>
                    ))}
                    {!watering.length && <tr><td colSpan={5} className="muted">No watering events yet</td></tr>}
                  </tbody>
                </table>
              </div>
              <AlertsPanel alerts={alerts} onAck={ack} />
            </section>

            {analytics && (
              <section className="analytics-row">
                <span>Avg moisture: <b>{analytics.avg_moisture}%</b></span>
                <span>Events (24h): <b>{analytics.watering_events}</b></span>
                <span>Water used: <b>{analytics.water_used_ml} ml</b></span>
                <span>Uptime: <b>{analytics.device_uptime_pct ?? "—"}%</b></span>
              </section>
            )}
          </>
        )}
      </main>
    </div>
  );
}
