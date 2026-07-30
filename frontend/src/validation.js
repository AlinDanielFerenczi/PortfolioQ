export function parseTickers(raw) {
  return raw
    .split(",")
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean);
}

export function validateForm(form) {
  const errors = [];
  const tickers = parseTickers(form.tickersRaw);

  if (tickers.length === 0) {
    errors.push("Enter at least one ticker.");
  }
  if (form.budget < 1 || form.budget > tickers.length) {
    errors.push(
      `Budget must be between 1 and ${tickers.length || "the number of tickers"} (got ${form.budget}).`
    );
  }

  const usesQaoa = form.method !== "classical";
  if (usesQaoa) {
    const minMaxiter = 2 * form.reps + 2;
    if (form.maxiter < minMaxiter) {
      errors.push(
        `maxiter must be at least 2*reps + 2 = ${minMaxiter} for reps=${form.reps} (got ${form.maxiter}).`
      );
    }
  }

  return { tickers, errors };
}

export function buildRequestBody(form) {
  const { tickers } = validateForm(form);
  return {
    tickers,
    budget: Number(form.budget),
    risk_factor: Number(form.risk_factor),
    reps: Number(form.reps),
    shots: Number(form.shots),
    maxiter: Number(form.maxiter),
    backend: form.backend.trim() || "aer_simulator",
    mixer_topology: form.mixer_topology,
    lookback_days: Number(form.lookback_days),
  };
}
