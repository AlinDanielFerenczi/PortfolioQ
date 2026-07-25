from fastapi import FastAPI, HTTPException

from schemas import OptimizeRequest, OptimizeResult, CompareAllResponse
from portfolio import prices_to_returns_and_cov, build_quadratic_program
from classical_solver import solve_classical_exact, solve_classical_greedy
from qaoa_solver import solve_qaoa
from xy_mixer_solver import solve_xy_qaoa


app = FastAPI(
    title="QAOA Portfolio Optimization Pilot",
    description=(
        "Template for benchmarking QAOA-based cardinality-constrained portfolio "
        "selection against classical baselines. Defaults to a noiseless simulator; "
        "swap `backend` to a real IBM Quantum device name to test on hardware. "
        "See README for realistic scale expectations (aim for 10-30 assets, not 100+)."
    ),
    version="0.1.0",
)


def _prepare_inputs(req: OptimizeRequest):
    if req.expected_returns is not None and req.covariances is not None:
        return req.expected_returns, req.covariances
    if req.prices is not None:
        mu, sigma = prices_to_returns_and_cov(req.prices)
        return mu.tolist(), sigma.tolist()
    raise HTTPException(
        status_code=400,
        detail="Provide either `prices`, or both `expected_returns` and `covariances`.",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize/classical", response_model=OptimizeResult)
def optimize_classical(req: OptimizeRequest, method: str = "exact"):
    mu, sigma = _prepare_inputs(req)
    try:
        if method == "greedy":
            result = solve_classical_greedy(req.tickers, mu, sigma, req.budget, req.risk_factor)
        else:
            result = solve_classical_exact(req.tickers, mu, sigma, req.budget, req.risk_factor)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OptimizeResult(method=f"classical_{method}", **result)


@app.post("/optimize/qaoa", response_model=OptimizeResult)
def optimize_qaoa(req: OptimizeRequest):
    mu, sigma = _prepare_inputs(req)
    try:
        qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
        result = solve_qaoa(qp, req.tickers, req.reps, req.shots, req.backend)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OptimizeResult(method="qaoa", **result)


@app.post("/optimize/compare-all", response_model=CompareAllResponse)
def optimize_compare(req: OptimizeRequest):
    mu, sigma = _prepare_inputs(req)
    try:
        classical = solve_classical_exact(req.tickers, mu, sigma, req.budget, req.risk_factor)
        qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
        qaoa_penalty = solve_qaoa(qp, req.tickers, req.reps, req.shots, req.backend)
        qaoa_xy = solve_xy_qaoa(
            qp, req.tickers, req.budget, req.reps, req.shots, req.backend, req.mixer_topology
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def pct_of_optimal(qaoa_obj_val):
        classical_obj = classical["objective_value"]
        if classical_obj == 0:
            return None
        gap = qaoa_obj_val - classical_obj  # >= 0 in theory; classical is optimal
        return 100.0 * (1.0 - gap / abs(classical_obj))

    return CompareAllResponse(
        classical=OptimizeResult(method="classical_exact", **classical),
        qaoa_penalty=OptimizeResult(method="qaoa_penalty", **qaoa_penalty),
        qaoa_xy_mixer=OptimizeResult(method="qaoa_xy_mixer", **qaoa_xy),
        qaoa_penalty_pct_of_optimal=pct_of_optimal(qaoa_penalty["objective_value"]),
        qaoa_xy_pct_of_optimal=pct_of_optimal(qaoa_xy["objective_value"]),
    )

@app.post("/optimize/qaoa-xy", response_model=OptimizeResult)
def optimize_qaoa_xy(req: OptimizeRequest):
    """Constraint-preserving QAOA: Dicke-state init + XY-mixer."""
    mu, sigma = _prepare_inputs(req)
    try:
        qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
        result = solve_xy_qaoa(
            qp, req.tickers, req.budget, req.reps, req.shots, req.backend, req.mixer_topology
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return OptimizeResult(method="qaoa_xy_mixer", **result)