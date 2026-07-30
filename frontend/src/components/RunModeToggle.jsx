export default function RunModeToggle({ mode, onChange, disabled }) {
  return (
    <div className="run-mode-toggle">
      <span className="field-label">Run mode</span>
      <div className="run-mode-options" role="radiogroup" aria-label="Run mode">
        <button
          type="button"
          className={`run-mode-option ${mode === "blocking" ? "run-mode-option-active" : ""}`}
          onClick={() => onChange("blocking")}
          disabled={disabled}
        >
          <span className="run-mode-option-title">Blocking</span>
          <span className="run-mode-option-desc">
            Waits for the result. Fine for the simulator — can hang for a long time on real
            hardware (each optimizer iteration is a hardware round-trip).
          </span>
        </button>
        <button
          type="button"
          className={`run-mode-option ${mode === "async" ? "run-mode-option-active" : ""}`}
          onClick={() => onChange("async")}
          disabled={disabled}
        >
          <span className="run-mode-option-title">Async (submit + poll)</span>
          <span className="run-mode-option-desc">
            Returns immediately and polls for status automatically. Recommended for real
            hardware.
          </span>
        </button>
      </div>
      {disabled && (
        <p className="field-hint">Classical solves are local and fast — always blocking.</p>
      )}
    </div>
  );
}
