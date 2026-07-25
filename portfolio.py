import numpy as np
import pandas as pd
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

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
