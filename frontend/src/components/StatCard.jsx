export default function StatCard({ icon, label, value, unit, warn }) {
  return (
    <div className={`stat-card ${warn ? "warn" : ""}`}>
      <div className="stat-icon">{icon}</div>
      <div>
        <div className="stat-value">{value ?? "—"}{value != null && unit}</div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}
