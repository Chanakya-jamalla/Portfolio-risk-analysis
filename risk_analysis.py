"""
risk_analysis.py
------------------
Reads price data OUT of the SQLite database built by fetch_data.py,
computes daily returns, and calculates portfolio Value-at-Risk (VaR)
using two methods: historical simulation and the parametric (variance
-covariance) approach.
"""

import sqlite3

import numpy as np
import pandas as pd
from scipy.stats import norm

DB_PATH = "portfolio.db"


def load_prices(tickers: list[str], db_path: str = DB_PATH) -> pd.DataFrame:
    """Pull prices for the given tickers out of the database as a wide table
    (one column per ticker, one row per date)."""
    conn = sqlite3.connect(db_path)
    placeholders = ",".join("?" for _ in tickers)
    query = f"""
        SELECT ticker, date, adj_close
        FROM prices
        WHERE ticker IN ({placeholders})
        ORDER BY date
    """
    df = pd.read_sql_query(query, conn, params=tickers)
    conn.close()

    if df.empty:
        raise ValueError(
            "No data found in the database for these tickers. "
            "Run fetch_data.py first."
        )

    df["date"] = pd.to_datetime(df["date"])
    prices = df.pivot(index="date", columns="ticker", values="adj_close").dropna()
    return prices


def compute_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily percentage returns for each ticker."""
    return prices.pct_change().dropna()


def portfolio_var(
    returns: pd.DataFrame,
    weights: list[float],
    confidence: float = 0.95,
    method: str = "historical",
) -> tuple[float, pd.Series]:
    """
    Calculate 1-day portfolio VaR.

    method="historical": looks at the worst actual days in the sample
        and reports the loss at the chosen percentile. Makes no
        assumption about the shape of the return distribution.

    method="parametric": assumes returns are roughly normally
        distributed, then uses the mean/standard deviation plus a
        z-score to estimate the loss threshold.
    """
    weights = np.array(weights)
    if not np.isclose(weights.sum(), 1.0):
        raise ValueError("weights must sum to 1.0")

    portfolio_returns = returns.dot(weights)

    if method == "historical":
        var = -np.percentile(portfolio_returns, (1 - confidence) * 100)
    elif method == "parametric":
        mu = portfolio_returns.mean()
        sigma = portfolio_returns.std()
        z = norm.ppf(1 - confidence)
        var = -(mu + z * sigma)
    else:
        raise ValueError("method must be 'historical' or 'parametric'")

    return var, portfolio_returns


def market_risk_summary(returns: pd.DataFrame, weights: list[float]) -> pd.DataFrame:
    """Per-asset volatility and correlation-adjusted contribution to
    portfolio risk -- a simple market risk breakdown."""
    weights = np.array(weights)
    cov_matrix = returns.cov() * 252  # annualised covariance
    portfolio_var_annual = weights.T @ cov_matrix.values @ weights
    portfolio_vol = np.sqrt(portfolio_var_annual)

    marginal_contribution = cov_matrix.values @ weights
    component_contribution = weights * marginal_contribution / portfolio_vol
    pct_contribution = component_contribution / portfolio_vol

    summary = pd.DataFrame(
        {
            "weight": weights,
            "annualised_volatility": np.sqrt(np.diag(cov_matrix.values)),
            "pct_of_portfolio_risk": pct_contribution,
        },
        index=returns.columns,
    )
    return summary
