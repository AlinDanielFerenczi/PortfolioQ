from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from schemas import OptimizeRequest, OptimizeResult, CompareAllResponse, JobSubmitted, JobStatus
from portfolio import prices_to_returns_and_cov, build_quadratic_program, fetch_prices
from classical_solver import solve_classical_exact, solve_classical_greedy
from qaoa_solver import solve_qaoa
from xy_mixer_solver import solve_xy_qaoa
from jobs import submit_job, get_job


app = FastAPI(
    title="QAOA Portfolio Optimization Pilot",
    description=(
        "Template for benchmarking QAOA-based cardinality-constrained portfolio "
        "selection against classical baselines. Defaults to a noiseless simulator; "
        "swap `backend` to a real IBM Quantum device name to test on hardware. "
        "On real hardware, prefer the `/submit` + `/jobs/{id}` endpoints over the "
        "blocking ones -- each COBYLA iteration is a hardware round-trip, and the "
        "blocking endpoints hold the HTTP connection open for all of them. "
        "See README for realistic scale expectations (aim for 10-30 assets, not 100+)."
    ),
    version="0.1.0",
)


@app.exception_handler(ValueError)
def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def _prepare_inputs(req: OptimizeRequest):
    if req.expected_returns is not None and req.covariances is not None:
        return req.expected_returns, req.covariances
    prices = req.prices
    if prices is None:
        prices = fetch_prices(req.tickers, req.lookback_days)
    mu, sigma = prices_to_returns_and_cov(prices)
    return mu.tolist(), sigma.tolist()


def _run_classical(req: OptimizeRequest, method: str) -> dict:
    mu, sigma = _prepare_inputs(req)
    if method == "greedy":
        result = solve_classical_greedy(req.tickers, mu, sigma, req.budget, req.risk_factor)
    else:
        result = solve_classical_exact(req.tickers, mu, sigma, req.budget, req.risk_factor)
    return {"method": f"classical_{method}", **result}


def _run_qaoa(req: OptimizeRequest) -> dict:
    mu, sigma = _prepare_inputs(req)
    qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
    result = solve_qaoa(qp, req.tickers, req.reps, req.shots, req.backend, req.maxiter)
    return {"method": "qaoa", **result}


def _run_qaoa_xy(req: OptimizeRequest) -> dict:
    mu, sigma = _prepare_inputs(req)
    qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
    result = solve_xy_qaoa(
        qp, req.tickers, req.budget, req.reps, req.shots, req.backend, req.mixer_topology, req.maxiter
    )
    return {"method": "qaoa_xy_mixer", **result}


def _run_compare_all(req: OptimizeRequest) -> dict:
    mu, sigma = _prepare_inputs(req)
    classical = solve_classical_exact(req.tickers, mu, sigma, req.budget, req.risk_factor)
    qp = build_quadratic_program(req.tickers, mu, sigma, req.budget, req.risk_factor)
    qaoa_penalty = solve_qaoa(qp, req.tickers, req.reps, req.shots, req.backend, req.maxiter)
    qaoa_xy = solve_xy_qaoa(
        qp, req.tickers, req.budget, req.reps, req.shots, req.backend, req.mixer_topology, req.maxiter
    )

    def pct_of_optimal(qaoa_obj_val):
        classical_obj = classical["objective_value"]
        if classical_obj == 0:
            return None
        gap = qaoa_obj_val - classical_obj  # >= 0 in theory; classical is optimal
        return 100.0 * (1.0 - gap / abs(classical_obj))

    return {
        "classical": {"method": "classical_exact", **classical},
        "qaoa_penalty": {"method": "qaoa_penalty", **qaoa_penalty},
        "qaoa_xy_mixer": {"method": "qaoa_xy_mixer", **qaoa_xy},
        "qaoa_penalty_pct_of_optimal": pct_of_optimal(qaoa_penalty["objective_value"]),
        "qaoa_xy_pct_of_optimal": pct_of_optimal(qaoa_xy["objective_value"]),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/optimize/classical", response_model=OptimizeResult)
def optimize_classical(req: OptimizeRequest, method: str = "exact"):
    return OptimizeResult(**_run_classical(req, method))


@app.post("/optimize/qaoa", response_model=OptimizeResult)
def optimize_qaoa(req: OptimizeRequest):
    return OptimizeResult(**_run_qaoa(req))


@app.post("/optimize/qaoa-xy", response_model=OptimizeResult)
def optimize_qaoa_xy(req: OptimizeRequest):
    """Constraint-preserving QAOA: Dicke-state init + XY-mixer."""
    return OptimizeResult(**_run_qaoa_xy(req))


@app.post("/optimize/compare-all", response_model=CompareAllResponse)
def optimize_compare(req: OptimizeRequest):
    return CompareAllResponse(**_run_compare_all(req))


@app.post("/optimize/qaoa/submit", response_model=JobSubmitted)
def submit_qaoa(req: OptimizeRequest):
    """Runs /optimize/qaoa in the background; poll /jobs/{job_id} for the result."""
    job_id = submit_job("qaoa", _run_qaoa, req)
    return JobSubmitted(job_id=job_id, status="pending")


@app.post("/optimize/qaoa-xy/submit", response_model=JobSubmitted)
def submit_qaoa_xy(req: OptimizeRequest):
    """Runs /optimize/qaoa-xy in the background; poll /jobs/{job_id} for the result."""
    job_id = submit_job("qaoa_xy_mixer", _run_qaoa_xy, req)
    return JobSubmitted(job_id=job_id, status="pending")


@app.post("/optimize/compare-all/submit", response_model=JobSubmitted)
def submit_compare_all(req: OptimizeRequest):
    """Runs /optimize/compare-all in the background; poll /jobs/{job_id} for the result."""
    job_id = submit_job("compare_all", _run_compare_all, req)
    return JobSubmitted(job_id=job_id, status="pending")


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobStatus(**job)
