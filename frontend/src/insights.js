const LOW_PCT_THRESHOLD = 90;
const NEAR_OPTIMAL_THRESHOLD = 99.9;

function sameSelection(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  const setA = new Set(a);
  return b.every((t) => setA.has(t));
}

export function buildConclusions(compare, reps) {
  if (!compare) return [];

  const variants = [
    {
      label: "QAOA (penalty)",
      result: compare.qaoa_penalty,
      pct: compare.qaoa_penalty_pct_of_optimal,
    },
    {
      label: "QAOA (XY-mixer)",
      result: compare.qaoa_xy_mixer,
      pct: compare.qaoa_xy_pct_of_optimal,
    },
  ];

  return variants.map(({ label, result, pct }) => {
    const matchesSelection = sameSelection(result.selected_assets, compare.classical.selected_assets);

    if (matchesSelection) {
      return {
        label,
        tone: "success",
        message: `${label} selected the same portfolio as the classical optimum (${result.selected_assets.join(", ")}).`,
      };
    }

    if (pct === null || pct === undefined) {
      return {
        label,
        tone: "info",
        message: `${label} selected a different portfolio than classical; % of optimal isn't available for this run (classical objective value is 0).`,
      };
    }

    if (pct >= NEAR_OPTIMAL_THRESHOLD) {
      return {
        label,
        tone: "success",
        message: `${label} reached the same objective value as classical (${pct.toFixed(1)}% of optimal) via a different, equally-good selection.`,
      };
    }

    if (pct < LOW_PCT_THRESHOLD) {
      return {
        label,
        tone: "warning",
        message: `${label} reached only ${pct.toFixed(1)}% of the optimal objective value. Try increasing reps (currently ${reps}) for a deeper circuit, or raising maxiter for a more thorough optimizer search.`,
      };
    }

    return {
      label,
      tone: "info",
      message: `${label} reached ${pct.toFixed(1)}% of the optimal objective value — close, but not an exact match.`,
    };
  });
}
