import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const COLORS = {
  classical: "#6b7280",
  penalty: "#2563eb",
  xy: "#16a34a",
};

export default function ComparisonCharts({ compare }) {
  if (!compare) return null;

  const objectiveData = [
    { name: "Classical", value: compare.classical.objective_value },
    { name: "QAOA (penalty)", value: compare.qaoa_penalty.objective_value },
    { name: "QAOA (XY-mixer)", value: compare.qaoa_xy_mixer.objective_value },
  ];

  const pctData = [
    { name: "QAOA (penalty)", value: compare.qaoa_penalty_pct_of_optimal },
    { name: "QAOA (XY-mixer)", value: compare.qaoa_xy_pct_of_optimal },
  ].filter((d) => d.value !== null && d.value !== undefined);

  const penaltyMeta = compare.qaoa_penalty.metadata || {};
  const xyMeta = compare.qaoa_xy_mixer.metadata || {};
  const gateData = [
    {
      name: "QAOA (penalty)",
      circuit_depth: penaltyMeta.circuit_depth,
      two_qubit_gates: penaltyMeta.two_qubit_gates,
    },
    {
      name: "QAOA (XY-mixer)",
      circuit_depth: xyMeta.circuit_depth,
      two_qubit_gates: xyMeta.two_qubit_gates,
    },
  ];

  return (
    <div className="charts-grid">
      <div className="chart-card">
        <h4>Objective value (lower is better)</h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={objectiveData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="value" fill={COLORS.penalty} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="chart-card">
        <h4>% of true optimum (classical = 100%)</h4>
        {pctData.length === 0 ? (
          <p className="field-hint">Not available (classical objective value is 0).</p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={pctData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis domain={[0, 110]} />
              <Tooltip formatter={(v) => `${v.toFixed(1)}%`} />
              <ReferenceLine y={100} stroke={COLORS.classical} strokeDasharray="4 4" label="optimal" />
              <Bar dataKey="value" fill={COLORS.xy} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="chart-card chart-card-wide">
        <h4>Circuit cost (depth &amp; two-qubit gates)</h4>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={gateData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="circuit_depth" fill={COLORS.penalty} name="Circuit depth" radius={[4, 4, 0, 0]} />
            <Bar dataKey="two_qubit_gates" fill={COLORS.xy} name="Two-qubit gates" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
