"""Fetch 8-K filings for S&P 500 companies from SEC EDGAR."""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv
from lxml import html as lxml_html
from tqdm import tqdm

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data/{cik_int}/{accession_nodash}/{doc}"

LOOKBACK_DAYS = 730  # ~2 years


def get_recent_8k_filings(cik: str, user_agent: str, lookback_days: int = LOOKBACK_DAYS) -> list[dict]:
    """Return metadata for recent 8-K filings for a given CIK."""
    url = SUBMISSIONS_URL.format(cik=cik)
    resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
    if resp.status_code != 200:
        return []
    data = resp.json()

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    cutoff = datetime.now() - timedelta(days=lookback_days)
    filings = []
    for form, date_str, accession, doc in zip(forms, dates, accessions, primary_docs):
        if form != "8-K":
            continue
        filing_date = datetime.strptime(date_str, "%Y-%m-%d")
        if filing_date < cutoff:
            continue
        filings.append(
            {
                "cik": cik,
                "form": form,
                "filing_date": date_str,
                "accession": accession,
                "primary_doc": doc,
            }
        )
    return filings


def html_to_text(raw_bytes: bytes) -> str:
    """Strip HTML/inline-XBRL markup down to plain text for LLM extraction."""
    try:
        tree = lxml_html.fromstring(raw_bytes)
        text = tree.text_content()
    except Exception:
        return raw_bytes.decode("utf-8", errors="ignore")
    return " ".join(text.split())


def fetch_filing_text(filing: dict, user_agent: str) -> str | None:
    cik_int = int(filing["cik"])
    accession_nodash = filing["accession"].replace("-", "")
    url = ARCHIVES_URL.format(cik_int=cik_int, accession_nodash=accession_nodash, doc=filing["primary_doc"])
    resp = requests.get(url, headers={"User-Agent": user_agent}, timeout=30)
    if resp.status_code != 200:
        return None
    return html_to_text(resp.content)


def main():
    load_dotenv()
    user_agent = os.environ.get("SEC_EDGAR_USER_AGENT", "unknown unknown@example.com")

    companies_path = RAW_DIR / "sp500_constituents.json"
    if not companies_path.exists():
        raise SystemExit("Run src/ingest/sp500.py first to generate sp500_constituents.json")

    companies = json.loads(companies_path.read_text())

    out_path = RAW_DIR / "sec_8k_filings.jsonl"
    with out_path.open("w") as out_f:
        for company in tqdm(companies, desc="Fetching 8-K filings"):
            filings = get_recent_8k_filings(company["cik"], user_agent)
            time.sleep(0.15)  # stay well under SEC's rate limit (10 req/sec)

            for filing in filings:
                text = fetch_filing_text(filing, user_agent)
                time.sleep(0.15)
                if not text:
                    continue
                record = {
                    "ticker": company["ticker"],
                    "company_name": company["company_name"],
                    "cik": company["cik"],
                    "filing_date": filing["filing_date"],
                    "accession": filing["accession"],
                    "source": "sec_8k",
                    "text": text,
                }
                out_f.write(json.dumps(record) + "\n")

    print(f"Wrote 8-K filings to {out_path}")


if __name__ == "__main__":
    main()
