"""Fetch the current S&P 500 constituent list and map tickers to SEC CIK numbers."""

import io
import json
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def fetch_sp500_constituents(user_agent: str) -> pd.DataFrame:
    """Scrape the S&P 500 table from Wikipedia (Symbol, Security, GICS Sector, ...)."""
    resp = requests.get(WIKI_URL, headers={"User-Agent": user_agent}, timeout=30)
    resp.raise_for_status()
    tables = pd.read_html(io.StringIO(resp.text))
    df = tables[0]
    df = df.rename(columns={"Symbol": "ticker", "Security": "company_name"})
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    return df[["ticker", "company_name"]]


def fetch_sec_ticker_cik_map(user_agent: str) -> dict:
    """SEC's ticker -> CIK mapping, required to look up filings per company."""
    resp = requests.get(SEC_TICKERS_URL, headers={"User-Agent": user_agent}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return {row["ticker"]: str(row["cik_str"]).zfill(10) for row in data.values()}


def build_sp500_with_cik(user_agent: str) -> pd.DataFrame:
    constituents = fetch_sp500_constituents(user_agent)
    ticker_to_cik = fetch_sec_ticker_cik_map(user_agent)
    constituents["cik"] = constituents["ticker"].map(ticker_to_cik)
    missing = constituents[constituents["cik"].isna()]
    if not missing.empty:
        print(f"Warning: {len(missing)} tickers had no CIK match: {missing['ticker'].tolist()}")
    return constituents.dropna(subset=["cik"])


def main():
    import os

    from dotenv import load_dotenv

    load_dotenv()
    user_agent = os.environ.get("SEC_EDGAR_USER_AGENT", "unknown unknown@example.com")

    df = build_sp500_with_cik(user_agent)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / "sp500_constituents.json"
    df.to_json(out_path, orient="records", indent=2)
    print(f"Wrote {len(df)} S&P 500 companies with CIK to {out_path}")


if __name__ == "__main__":
    main()
