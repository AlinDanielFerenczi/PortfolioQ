# QAOA Portfolio Optimization — Frontend

A small React (Vite) UI for the FastAPI backend in the repo root: builds
`/optimize/*` requests through a form instead of hand-written JSON, and
renders results — including the classical vs. penalty-QAOA vs. XY-mixer-QAOA
comparison charts (objective value, % of true optimum, circuit depth /
two-qubit gate count) from `/optimize/compare-all`.

## Setup

From the repo root, `npm run dev` starts this together with the backend in
one command (see the root [README.md](../README.md#frontend)). To run just
this piece on its own:

```bash
npm install
cp .env.example .env   # only needed if the backend isn't on localhost:8000
npm run dev
```

Opens on `http://localhost:5173`. The backend must be running separately:

```bash
# from the repo root, in another terminal
uvicorn main:app --reload
```

The backend's CORS config (`main.py`) already allows `localhost:5173` (Vite
dev) and `localhost:4173` (`vite preview`).

## What it does

- **Method selector**: Classical / QAOA (penalty) / QAOA (XY-mixer) / Compare
  All. Compare All is the default and renders the comparison charts.
- **Auto price fetch**: the form never sends `prices` — it relies on the
  backend's `yfinance` auto-fetch (`lookback_days`), same as calling the API
  without a `prices` field.
- **Inline validation**: mirrors the backend's own checks (`budget` within
  range, `maxiter >= 2*reps + 2`) before you can submit, to avoid a
  round-trip for an error the backend would reject anyway.
- **Run mode**: Blocking or Async. Defaults to Blocking when `backend` is
  `aer_simulator` and Async otherwise (real hardware runs can block for a
  long time — see the root README's "Async jobs" section) — but you can
  override it either way. Async mode submits to `/optimize/*/submit` and
  polls `/jobs/{id}` automatically every 2 seconds, showing live
  pending/running status and elapsed time until it completes or fails.
