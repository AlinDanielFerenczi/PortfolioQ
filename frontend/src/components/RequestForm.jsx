import { METHODS } from "../api";
import { validateForm } from "../validation";

const METHOD_ORDER = ["compare-all", "classical", "qaoa", "qaoa-xy"];
const BACKEND_PRESETS = ["aer_simulator", "ibm_kingston"];

export default function RequestForm({ form, onChange, disabled }) {
  const { errors } = validateForm(form);
  const isCustomBackend = !BACKEND_PRESETS.includes(form.backend);

  const set = (key) => (e) => {
    const value = e.target.type === "number" ? e.target.valueAsNumber : e.target.value;
    onChange({ [key]: Number.isNaN(value) ? "" : value });
  };

  return (
    <div className="request-form">
      <div className="field">
        <label className="field-label" htmlFor="method">Method</label>
        <div className="segmented" role="radiogroup" aria-label="Method">
          {METHOD_ORDER.map((key) => (
            <button
              type="button"
              key={key}
              className={form.method === key ? "segmented-active" : ""}
              onClick={() => onChange({ method: key })}
              disabled={disabled}
            >
              {METHODS[key].label}
            </button>
          ))}
        </div>
      </div>

      <div className="field">
        <label className="field-label" htmlFor="tickers">Tickers (comma-separated)</label>
        <input
          id="tickers"
          type="text"
          value={form.tickersRaw}
          onChange={(e) => onChange({ tickersRaw: e.target.value })}
          disabled={disabled}
        />
      </div>

      <div className="field-row">
        <div className="field">
          <label className="field-label" htmlFor="budget">Budget (# assets to select)</label>
          <input id="budget" type="number" min="1" value={form.budget} onChange={set("budget")} disabled={disabled} />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="risk_factor">Risk factor</label>
          <input id="risk_factor" type="number" step="0.1" value={form.risk_factor} onChange={set("risk_factor")} disabled={disabled} />
        </div>
        <div className="field">
          <label className="field-label" htmlFor="lookback_days">Lookback days (auto price fetch)</label>
          <input id="lookback_days" type="number" min="2" value={form.lookback_days} onChange={set("lookback_days")} disabled={disabled} />
        </div>
      </div>

      {form.method !== "classical" && (
        <>
          <div className="field-row">
            <div className="field">
              <label className="field-label" htmlFor="reps">reps (QAOA layers)</label>
              <input id="reps" type="number" min="1" value={form.reps} onChange={set("reps")} disabled={disabled} />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="shots">shots</label>
              <input id="shots" type="number" min="1" value={form.shots} onChange={set("shots")} disabled={disabled} />
            </div>
            <div className="field">
              <label className="field-label" htmlFor="maxiter">
                maxiter (min {2 * form.reps + 2} for reps={form.reps})
              </label>
              <input id="maxiter" type="number" min="1" value={form.maxiter} onChange={set("maxiter")} disabled={disabled} />
            </div>
          </div>

          <div className="field-row">
            <div className="field">
              <label className="field-label" htmlFor="backend">Backend</label>
              <select
                id="backend"
                value={isCustomBackend ? "custom" : form.backend}
                onChange={(e) => onChange({ backend: e.target.value === "custom" ? "" : e.target.value })}
                disabled={disabled}
              >
                <option value="aer_simulator">aer_simulator (simulator)</option>
                <option value="ibm_kingston">ibm_kingston</option>
                <option value="custom">Custom…</option>
              </select>
              {isCustomBackend && (
                <input
                  type="text"
                  value={form.backend}
                  onChange={(e) => onChange({ backend: e.target.value })}
                  placeholder="e.g. ibm_torino"
                  disabled={disabled}
                />
              )}
            </div>
            {(form.method === "qaoa-xy" || form.method === "compare-all") && (
              <div className="field">
                <label className="field-label" htmlFor="mixer_topology">Mixer topology</label>
                <select
                  id="mixer_topology"
                  value={form.mixer_topology}
                  onChange={(e) => onChange({ mixer_topology: e.target.value })}
                  disabled={disabled}
                >
                  <option value="ring">ring</option>
                  <option value="complete">complete</option>
                </select>
              </div>
            )}
          </div>
        </>
      )}

      {errors.length > 0 && (
        <ul className="field-errors">
          {errors.map((err) => (
            <li key={err}>{err}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
