"""Fetch financial news headlines for S&P 500 companies via GDELT's free DOC API."""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from tqdm import tqdm

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

LOOKBACK_DAYS = 730
MAX_RECORDS_PER_COMPANY = 25


def fetch_news_for_company(company_name: str) -> list[dict]:
    start = (datetime.now() - timedelta(days=LOOKBACK_DAYS)).strftime("%Y%m%d%H%M%S")
    end = datetime.now().strftime("%Y%m%d%H%M%S")

    params = {
        "query": f'"{company_name}" (acquisition OR merger OR CEO OR resign OR appoint)',
        "mode": "artlist",
        "format": "json",
        "maxrecords": MAX_RECORDS_PER_COMPANY,
        "startdatetime": start,
        "enddatetime": end,
        "sort": "hybridrel",
    }
    resp = requests.get(GDELT_URL, params=params, timeout=30)
    if resp.status_code != 200:
        return []
    try:
        data = resp.json()
    except ValueError:
        return []
    return data.get("articles", [])


def main():
    companies_path = RAW_DIR / "sp500_constituents.json"
    if not companies_path.exists():
        raise SystemExit("Run src/ingest/sp500.py first to generate sp500_constituents.json")

    companies = json.loads(companies_path.read_text())

    out_path = RAW_DIR / "news_articles.jsonl"
    with out_path.open("w") as out_f:
        for company in tqdm(companies, desc="Fetching news"):
            articles = fetch_news_for_company(company["company_name"])
            time.sleep(1.0)  # be polite to GDELT's free endpoint

            for article in articles:
                title = article.get("title")
                if not title:
                    continue
                record = {
                    "ticker": company["ticker"],
                    "company_name": company["company_name"],
                    "source": "news",
                    "url": article.get("url"),
                    "seendate": article.get("seendate"),
                    "text": title,
                }
                out_f.write(json.dumps(record) + "\n")

    print(f"Wrote news articles to {out_path}")


if __name__ == "__main__":
    main()
