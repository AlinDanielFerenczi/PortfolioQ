# QAOA Portfolio Optimization Pilot

A FastAPI template for benchmarking QAOA-based, cardinality-constrained
portfolio selection against classical baselines. Tested end-to-end against
Qiskit 2.x / qiskit-optimization 0.7 / qiskit-algorithms on a local
`aer_simulator` run.

## Limitations

This is a **pilot / capability-building scaffold**, not a production
optimizer, and it will not beat classical solvers at real portfolio sizes.
Cap it around **10-30 assets** for anything you actually run on real hardware.

## Constraint handling: penalty method vs. Dicke-state/XY-mixer

`/optimize/qaoa` uses the standard `QuadraticProgramToQubo` penalty-method
conversion: simple, but it spends circuit depth and tuning effort on
constraint enforcement, and some fraction of samples can violate the
budget constraint entirely (they just get scored badly by the penalty term).

`/optimize/qaoa-xy` implements the stronger approach from recent literature:
a **Dicke-state initialization** (...built via `build_dicke_circuit`, using a
small ancilla "running count" register that provably ends at exactly
`|budget>` and resets cleanly to `|0>`) combined with an **XY-mixer**
(`RXX``RYY` gates, verified directly against the matrix exponential, not
just assumed). Together these keep every measurement inside the feasible
subspace.

The classical optimizer loop (COBYLA) uses
a random initial guess, so repeated runs can converge to different local
optima... run it a few times and keep the best, or increase `reps`.

## Components

- `portfolio.py` — builds a Markowitz mean-variance `QuadraticProgram`
  (minimize `risk_factor * w^T Sigma w - mu^T w`, subject to `sum(w) == budget`,
  `w` binary) either from raw historical prices or from a supplied
  expected-returns/covariance pair.
- `classical_solver.py` — two baselines: exact enumeration (brute-forces
  all `C(n, budget)` feasible selections directly, so the cardinality
  constraint doesn't need penalty tuning — fine up to the low 30s in `n`) and
  a greedy heuristic (the "what we'd run in production today" comparison).
- `qaoa_solver.py` — penalty-method QAOA: builds the circuit from the QUBO's Ising Hamiltonian, runs it via `qiskit_algorithms.QAOA` `MinimumEigenOptimizer`, and reports circuit metadata (total gates, two-qubit gate count, depth) alongside the result so you can sanity-check against your hardware's real gate budget (order of a few thousand two-qubit gates on current 156-qubit devices).
- `xy_mixer_solver.py` — **constraint-preserving QAOA**: Dicke-state initialization XY-mixer, so the circuit only ever explores the feasible K-of-N subspace, no penalty-term tuning needed. See "Constraint handling" below.
- `main.py` — endpoints: `/optimize/classical`, `/optimize/qaoa` (penalty method), `/optimize/qaoa-xy` (Dicke/XY-mixer), `/optimize/compare-all` (all three methods, with each QAOA variant's % of the true optimum), plus `/submit` + `/jobs/{id}` async variants of the three QAOA/compare endpoints.
- `jobs.py` — minimal in-memory background job runner backing the `/submit` + `/jobs/{id}` endpoints (thread pool, no persistence — see "Async jobs" below).

## Setup

```bash
python3 -m venv venv
. venv/bin/activate
pip install -r requirements.txt
```

Run locally (simulator only, no credentials needed):

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000/docs` for interactive API docs.

### Running on real IBM hardware

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```
IBM_QUANTUM_TOKEN=your_ibm_cloud_api_key
IBM_QUANTUM_INSTANCE=crn:v1:bluemix:public:quantum-computing:us-east:a/xxxxxxxx:yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy::
```

As of the 2025 IBM Quantum Platform migration, this connects via the
`ibm_quantum_platform` channel, which uses IBM Cloud auth: `IBM_QUANTUM_TOKEN`
is an IBM Cloud API key (from the IBM Cloud console, not the old classic
quantum.ibm.com token), and `IBM_QUANTUM_INSTANCE` is the full CRN of your
Quantum service instance (from quantum.cloud.ibm.com).

`config.py` loads `.env` automatically via `python-dotenv`. Environment
variables set another way (e.g. `export IBM_QUANTUM_TOKEN=...`) still work
and take precedence if both are set.

Then set `"backend"` in your request to a real device name (e.g.
`"ibm_torino"`) instead of `"aer_simulator"`.

### Async jobs (recommended for real hardware)

`/optimize/qaoa` and `/optimize/qaoa-xy` run COBYLA classically, and each
iteration submits a job to `backend` and blocks on `.result()` until it
clears the IBM queue — by default up to `maxiter` (100) hardware round-trips
per request. On the simulator that's instant; on real hardware the request
can hang well past typical HTTP/client timeouts.

Two ways to handle this:

- Lower `maxiter` (e.g. 3-5) for an initial timing check before scaling up.
- Use the async variants instead of blocking the connection:
  - `POST /optimize/qaoa/submit`, `POST /optimize/qaoa-xy/submit`,
    `POST /optimize/compare-all/submit` — same request body, returns
    `{"job_id": ..., "status": "pending"}` immediately.
  - `GET /jobs/{job_id}` — poll for `status` (`pending`/`running`/
    `completed`/`failed`), `result`, or `error`.

Jobs run in an in-process thread pool and are held in memory — they don't
survive a server restart and aren't shared across multiple worker processes.
Fine for this pilot's single-process usage; swap in a real task queue
(Celery/RQ + Redis, etc.) before running this multi-worker or in production.

## Automatic price data

If a request omits both `prices` and `expected_returns`/`covariances`, all
endpoints fetch `lookback_days` (default 30) of daily closes for `tickers`
from `yfinance` automatically:

```json
POST /optimize/compare-all
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "budget": 2,
  "risk_factor": 0.5
}
```

## Example request

```json
POST /optimize/compare-all
{
  "tickers": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
  "prices": {
    "AAPL":  [150.2, 151.0, 149.8, 152.3, 153.1],
    "MSFT":  [280.1, 281.5, 279.9, 283.0, 282.4],
    "GOOGL": [98.4, 99.1, 97.8, 99.9, 100.2],
    "AMZN":  [102.6, 101.9, 103.4, 104.0, 103.7],
    "NVDA":  [45.3, 46.1, 45.9, 47.2, 48.0]
  },
  "budget": 2,
  "risk_factor": 0.5,
  "reps": 2,
  "shots": 1024,
  "backend": "aer_simulator"
}
```

Response includes both solvers' selected assets, objective values, and
`qaoa_penalty_pct_of_optimal` / `qaoa_xy_pct_of_optimal` (100% means QAOA
found the true optimum on this run).

A value of 100% for `pct_of_optimal` means QAOA's selection has the exact same objective value
as the true optimum. Values below 100% mean it fell short, by roughly that
percentage of the optimal objective's magnitude.

## Real use case

1. Swap in real historical price data for your actual candidate universe
   (10-30 tickers).
2. Run `/optimize/compare-all` on the simulator to see classical exact,
   penalty-method QAOA, and Dicke/XY-mixer QAOA side by side, check
   `feasible_fraction` on the XY-mixer result (should be 1.0) and compare
   `circuit_depth`/`two_qubit_gates` between the two QAOA variants.
3. Run the same request against a real IBM backend and chart result quality
   vs. gate count as you increase `reps`, this is the "signal vs. noise
   crossover" chart that's the actual deliverable for a business-case pitch.
   Expect `feasible_fraction` to drop below 1.0 on real hardware even for
   the XY-mixer, since noise (not the algorithm) is what breaks the
   Hamming-weight preservation there, that gap is itself a meaningful
   data point.
