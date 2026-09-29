export default function DeviceCard({ device, onSelect, active }) {
  const statusColor = device.status === "online" ? "#2ecc71" : "#e74c3c";
  const healthColor = { Healthy: "#2ecc71", "Needs Water": "#f39c12", Critical: "#e74c3c", Unknown: "#95a5a6" }[device.plant_health];
  return (
    <div className={`device-card ${active ? "active" : ""}`} onClick={() => onSelect(device.device_id)}>
      <div className="device-card-top">
        <strong>{device.plant_name}</strong>
        <span className="dot" style={{ background: statusColor }} title={device.status} />
      </div>
      <div className="muted small">{device.device_id} · {device.plant_type}</div>
      <div className="badge" style={{ background: healthColor }}>{device.plant_health}</div>
      {device.latest && <div className="mini-stat">💧 {device.latest.soil_moisture}%</div>}
    </div>
  );
}
