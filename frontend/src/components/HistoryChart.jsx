import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const fmt = (t) => new Date(t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export default function HistoryChart({ title, data, lines }) {
  return (
    <div className="chart-card">
      <h3>{title}</h3>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a3b2f" />
          <XAxis dataKey="timestamp" tickFormatter={fmt} minTickGap={30} stroke="#7fa88a" />
          <YAxis stroke="#7fa88a" />
          <Tooltip labelFormatter={fmt} contentStyle={{ background: "#12241a", border: "1px solid #2a3b2f" }} />
          <Legend />
          {lines.map((l) => (
            <Line key={l.key} type="monotone" dataKey={l.key} name={l.name} stroke={l.color} dot={false} strokeWidth={2} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
