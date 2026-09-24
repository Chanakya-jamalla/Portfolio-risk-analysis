"""
main.py
--------
Runs the full pipeline:
  1. Make sure the SQLite database has fresh price data (fetch_data.py)
  2. Load it back out with plain SQL (risk_analysis.py)
  3. Compute daily returns
  4. Calculate 1-day 95% VaR, both historical and parametric
  5. Print a market-risk breakdown per asset
  6. Save a chart of the return distribution with the VaR line marked

Run with:
    python main.py
"""

import matplotlib.pyplot as plt

from fetch_data import DEFAULT_TICKERS, fetch_and_store
from risk_analysis import compute_returns, load_prices, market_risk_summary, portfolio_var

TICKERS = DEFAULT_TICKERS
WEIGHTS = [0.25, 0.25, 0.20, 0.20, 0.10]  # must sum to 1.0, matches TICKERS order
CONFIDENCE = 0.95


def main():
    print("Step 1: refreshing database from Yahoo Finance...")
    fetch_and_store(TICKERS)

    print("\nStep 2: loading prices back out of the database...")
    prices = load_prices(TICKERS)
    returns = compute_returns(prices)
    print(f"Loaded {len(returns)} days of returns for {TICKERS}")

    print("\nStep 3: calculating VaR...")
    var_hist, portfolio_returns = portfolio_var(returns, WEIGHTS, CONFIDENCE, method="historical")
    var_param, _ = portfolio_var(returns, WEIGHTS, CONFIDENCE, method="parametric")

    print(f"\n1-day {int(CONFIDENCE*100)}% VaR (historical):  {var_hist:.2%}")
    print(f"1-day {int(CONFIDENCE*100)}% VaR (parametric):  {var_param:.2%}")
    print("\n(Interpretation: on a normal bad day, this portfolio should not")
    print(f" lose more than about {var_hist:.2%} of its value, {int(CONFIDENCE*100)}% of the time.)")

    print("\nStep 4: market risk breakdown by asset...")
    print(market_risk_summary(returns, WEIGHTS).round(4))

    print("\nStep 5: saving chart to var_distribution.png ...")
    plt.figure(figsize=(10, 5))
    plt.hist(portfolio_returns, bins=50, color="#4C72B0", alpha=0.85, edgecolor="white")
    plt.axvline(-var_hist, color="crimson", linestyle="--", linewidth=2,
                label=f"Historical VaR ({int(CONFIDENCE*100)}%): {var_hist:.2%}")
    plt.title("Portfolio Daily Returns with Value-at-Risk")
    plt.xlabel("Daily Return")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig("var_distribution.png", dpi=150)
    print("Done.")


if __name__ == "__main__":
    main()
