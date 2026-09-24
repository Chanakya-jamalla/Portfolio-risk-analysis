"""
fetch_data.py
--------------
Downloads real daily stock prices from Yahoo Finance (via the yfinance
library) and stores them in a local SQLite database (portfolio.db).

This is the "real database" step: instead of keeping price data as a
CSV or inside the code, every price gets written to a proper SQL
table that other scripts (risk_analysis.py) query with normal SQL.

Run this file directly to (re)build the database:
    python fetch_data.py
"""

import sqlite3
from datetime import datetime

import pandas as pd
import yfinance as yf

DB_PATH = "portfolio.db"

# Deutsche Bank (DBK.DE) is included deliberately -- this project is
# meant to sit alongside the DB valuation project on the resume.
DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "DBK.DE"]


def create_database(db_path: str = DB_PATH) -> None:
    """Create the prices table if it doesn't already exist."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS prices (
            ticker    TEXT NOT NULL,
            date      TEXT NOT NULL,
            adj_close REAL NOT NULL,
            PRIMARY KEY (ticker, date)
        )
        """
    )
    conn.commit()
    conn.close()


def fetch_and_store(
    tickers: list[str] = DEFAULT_TICKERS,
    start: str = "2022-01-01",
    end: str | None = None,
    db_path: str = DB_PATH,
) -> None:
    """Download each ticker from Yahoo Finance and upsert it into SQLite."""
    end = end or datetime.today().strftime("%Y-%m-%d")
    create_database(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for ticker in tickers:
        print(f"Downloading {ticker} ({start} to {end}) ...")
        data = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False)

        if data.empty:
            print(f"  no data returned for {ticker}, skipping")
            continue

        # yfinance returns a MultiIndex column when >1 ticker is passed at
        # once; since we download one at a time here, flatten just in case.
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        prices = data[["Adj Close"]].reset_index()
        prices.columns = ["date", "adj_close"]
        prices["date"] = pd.to_datetime(prices["date"]).dt.strftime("%Y-%m-%d")

        rows = [(ticker, row.date, float(row.adj_close)) for row in prices.itertuples(index=False)]
        cursor.executemany(
            "INSERT OR REPLACE INTO prices (ticker, date, adj_close) VALUES (?, ?, ?)",
            rows,
        )
        conn.commit()
        print(f"  stored {len(rows)} rows for {ticker}")

    conn.close()
    print(f"\nDone. Data is in {db_path} -> table 'prices'")


if __name__ == "__main__":
    fetch_and_store()
