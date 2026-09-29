const SEV = { INFO: "#3498db", WARNING: "#f39c12", CRITICAL: "#e74c3c" };

export default function AlertsPanel({ alerts, onAck }) {
  if (!alerts.length) return <div className="alerts-panel"><h3>Alerts</h3><p className="muted">No open alerts 🎉</p></div>;
  return (
    <div className="alerts-panel">
      <h3>Alerts</h3>
      {alerts.map((a) => (
        <div key={a.alert_id} className="alert-row">
          <span className="sev-dot" style={{ background: SEV[a.severity] }} />
          <div className="alert-msg">
            <div>{a.message}</div>
            <div className="muted small">{new Date(a.created_at).toLocaleString()} · {a.status}</div>
          </div>
          {a.status === "OPEN" && <button className="ack-btn" onClick={() => onAck(a.alert_id)}>Ack</button>}
        </div>
      ))}
    </div>
  );
}
