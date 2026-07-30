import { buildConclusions } from "../insights";

export default function ConclusionPanel({ compare, reps }) {
  const conclusions = buildConclusions(compare, reps);
  if (conclusions.length === 0) return null;

  return (
    <div className="conclusion-panel">
      <h4>Conclusion</h4>
      <ul className="conclusion-list">
        {conclusions.map((c) => (
          <li key={c.label} className={`conclusion-item conclusion-${c.tone}`}>
            {c.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
