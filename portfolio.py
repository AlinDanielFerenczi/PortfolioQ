import numpy as np
import pandas as pd
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo


def fetch_prices(tickers: list, lookback_days: int = 30, retries: int = 3) -> dict:
    import time
    import yfinance as yf

    data = None
    last_error = None
    for attempt in range(retries):
        try:
            downloaded = yf.download(
                tickers, period=f"{lookback_days}d", interval="1d", auto_adjust=True, progress=False
            )["Close"]
        except Exception as e:
            last_error = e
            downloaded = None

        if downloaded is not None:
            if isinstance(downloaded, pd.Series):
                downloaded = downloaded.to_frame(name=tickers[0])
            downloaded = downloaded.dropna()
            if not downloaded.empty:
                data = downloaded
                break

        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))

    if data is None:
        detail = f": {last_error}" if last_error else " (empty response, possibly rate-limited)"
        raise ValueError(f"yfinance returned no price data for {tickers} after {retries} attempts{detail}")

    missing = [t for t in tickers if t not in data.columns]
    if missing:
        raise ValueError(f"yfinance returned no price data for: {missing}")
    if len(data) < 2:
        raise ValueError(
            f"yfinance returned only {len(data)} trading day(s) for {tickers}; "
            "need at least 2 to compute returns. Try a larger lookback_days."
        )
    return {t: data[t].tolist() for t in tickers}


def prices_to_returns_and_cov(prices: dict):
    df = pd.DataFrame(prices)
    pct = df.pct_change().dropna()
    expected_returns = pct.mean().values
    covariances = pct.cov().values
    return expected_returns, covariances


def build_quadratic_program(
    tickers: list,
    expected_returns: list,
    covariances: list,
    budget: int,
    risk_factor: float = 0.5,
):
    n = len(tickers)
    if budget < 1 or budget > n:
        raise ValueError("budget must be between 1 and the number of tickers")

    mu = np.array(expected_returns)
    sigma = np.array(covariances)

    # Manual build: qiskit-finance's PortfolioOptimization helper (which used
    # to wrap this) has been retired, so we construct the QuadraticProgram
    # directly. Objective: minimize risk_factor * w^T Sigma w - mu^T w,
    # subject to sum(w) == budget, w_i binary.
    qp = QuadraticProgram(name="portfolio_optimization")
    for t in tickers:
        qp.binary_var(name=t)

    linear = {tickers[i]: -mu[i] for i in range(n)}
    quadratic = {
        (tickers[i], tickers[j]): risk_factor * sigma[i, j]
        for i in range(n)
        for j in range(n)
        if sigma[i, j] != 0
    }
    qp.minimize(linear=linear, quadratic=quadratic)
    qp.linear_constraint(
        linear={t: 1 for t in tickers}, sense="==", rhs=budget, name="budget"
    )
    return qp


def qubo_and_gate_estimate(qp):
    converter = QuadraticProgramToQubo()
    qubo = converter.convert(qp)
    num_vars = qubo.get_num_vars()
    return qubo, converter, num_vars
