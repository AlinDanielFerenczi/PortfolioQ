import itertools
import math
import numpy as np

def _objective(selection: set, mu: np.ndarray, sigma: np.ndarray, risk_factor: float) -> float:
    """Markowitz objective for a fixed asset selection: risk*w^T Sigma w - mu^T w,
    with w_i = 1 for selected assets, 0 otherwise (matches PortfolioOptimization's
    default unit-weight convention)."""
    idx = list(selection)
    w = np.zeros(len(mu))
    w[idx] = 1.0
    return float(risk_factor * w @ sigma @ w - mu @ w)


def solve_classical_exact(
    tickers: list, expected_returns: list, covariances: list, budget: int, risk_factor: float = 0.5
):
    """
    Exact brute-force solve by enumerating all C(n, budget) feasible
    selections directly, no penalty terms needed since the cardinality
    constraint is respected by construction. Fine for n up to the low
    30s; for larger n this becomes intractable, at which point you'd
    swap in Gurobi/CPLEX (drop-in replacement for this function).
    """
    n = len(tickers)
    mu = np.array(expected_returns)
    sigma = np.array(covariances)

    num_combos = math.comb(n, budget)
    best_val = None
    best_sel = None
    for combo in itertools.combinations(range(n), budget):
        val = _objective(set(combo), mu, sigma, risk_factor)
        if best_val is None or val < best_val:
            best_val = val
            best_sel = combo

    bitstring = "".join("1" if i in best_sel else "0" for i in range(n))
    return {
        "selected_assets": [tickers[i] for i in best_sel],
        "bitstring": bitstring,
        "objective_value": best_val,
        "metadata": {"method": "exact_enumeration", "combinations_evaluated": num_combos},
    }


def solve_classical_greedy(
    tickers: list, expected_returns: list, covariances: list, budget: int, risk_factor: float = 0.5
):
    """
    Fast greedy heuristic baseline: repeatedly add the asset that most
    improves the objective. Useful as the 'what we'd actually run in
    production today' comparison point, since exact enumeration doesn't
    scale past a few dozen assets.
    """
    n = len(tickers)
    mu = np.array(expected_returns)
    sigma = np.array(covariances)

    selected = set()
    remaining = set(range(n))
    for _ in range(budget):
        best_asset, best_val = None, None
        for i in remaining:
            val = _objective(selected | {i}, mu, sigma, risk_factor)
            if best_val is None or val < best_val:
                best_val, best_asset = val, i
        selected.add(best_asset)
        remaining.remove(best_asset)

    bitstring = "".join("1" if i in selected else "0" for i in range(n))
    return {
        "selected_assets": [tickers[i] for i in selected],
        "bitstring": bitstring,
        "objective_value": _objective(selected, mu, sigma, risk_factor),
        "metadata": {"method": "greedy"},
    }
