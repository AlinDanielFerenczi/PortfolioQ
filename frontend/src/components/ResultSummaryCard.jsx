export default function ResultSummaryCard({ result }) {
  if (!result) return null;
  const metadataEntries = Object.entries(result.metadata || {});

  return (
    <div className="result-card">
      <h3>{result.method}</h3>
      <div className="result-row">
        <span className="result-label">Selected assets</span>
        <div className="chip-row">
          {result.selected_assets.map((t) => (
            <span className="chip" key={t}>{t}</span>
          ))}
        </div>
      </div>
      <div className="result-row">
        <span className="result-label">Objective value</span>
        <span className="result-value">{result.objective_value.toFixed(6)}</span>
      </div>
      <div className="result-row">
        <span className="result-label">Bitstring</span>
        <span className="result-value mono">{result.bitstring}</span>
      </div>
      {metadataEntries.length > 0 && (
        <details className="metadata-details">
          <summary>Metadata</summary>
          <table className="metadata-table">
            <tbody>
              {metadataEntries.map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{typeof value === "number" ? Number(value.toFixed(6)) : String(value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
    </div>
  );
}
