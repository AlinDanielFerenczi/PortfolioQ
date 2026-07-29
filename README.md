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
- `main.py` — endpoints: `/optimize/classical`, `/optimize/qaoa` (penalty method), `/optimize/qaoa-xy` (Dicke/XY-mixer), `/optimize/compare-all` (all three methods, with each QAOA variant's % of the true optimum).

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

```bash
export IBM_QUANTUM_TOKEN="your_token_here"
export IBM_QUANTUM_INSTANCE="ibm-q/open/main"   # or your instance string
```

Then set `"backend"` in your request to a real device name (e.g.
`"ibm_torino"`) instead of `"aer_simulator"`.

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
