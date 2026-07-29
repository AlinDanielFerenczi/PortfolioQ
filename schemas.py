from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class OptimizeRequest(BaseModel):
    tickers: List[str] = Field(..., description="Asset symbols, in order")
    prices: Optional[Dict[str, List[float]]] = Field(
        None, description="ticker -> list of historical prices (same length, same order)"
    )
    expected_returns: Optional[List[float]] = Field(
        None, description="Expected return per asset, same order as tickers"
    )
    covariances: Optional[List[List[float]]] = Field(
        None, description="Covariance matrix, same order as tickers"
    )
    lookback_days: int = Field(
        30,
        description=(
            "If neither `prices` nor `expected_returns`/`covariances` are given, "
            "fetch this many days of daily closes from yfinance for `tickers` instead."
        ),
    )
    budget: int = Field(..., description="Number of assets to select (cardinality constraint K)")
    risk_factor: float = Field(0.5, description="Risk aversion weight (higher = more risk-averse)")
    reps: int = Field(1, description="Number of QAOA layers (p)")
    shots: int = Field(1024, description="Number of measurement shots for QAOA sampling")
    maxiter: int = Field(
        100,
        description=(
            "Max COBYLA iterations. Each iteration submits a job to `backend`, so on "
            "real hardware this is roughly the number of hardware round-trips the "
            "request will block on. Keep this low (e.g. 3-5) for an initial timing "
            "check before scaling up, or use the /submit + /jobs/{id} endpoints "
            "instead of blocking the request."
        ),
    )
    backend: str = Field(
        "aer_simulator",
        description="'aer_simulator' for noiseless sim, or an IBM Quantum backend name for real hardware",
    )
    mixer_topology: str = Field(
        "ring", description="XY-mixer connectivity for the constraint-preserving solver: 'ring' or 'complete'"
    )


class OptimizeResult(BaseModel):
    method: str
    selected_assets: List[str]
    bitstring: str
    objective_value: float
    metadata: Dict = {}


class CompareAllResponse(BaseModel):
    classical: OptimizeResult
    qaoa_penalty: OptimizeResult
    qaoa_xy_mixer: OptimizeResult
    qaoa_penalty_pct_of_optimal: Optional[float] = None
    qaoa_xy_pct_of_optimal: Optional[float] = None


class JobSubmitted(BaseModel):
    job_id: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    method: str
    status: str
    submitted_at: str
    completed_at: Optional[str] = None
    result: Optional[Dict] = None
    error: Optional[str] = None