"""Orchestrates extraction: read raw docs -> chunk -> LLM extract -> validate -> write triples JSONL."""

import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm

from src.extraction.ollama_client import extract_triples

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

CHUNK_SIZE = 3000  # chars; keeps prompts within a local 8B model's comfortable context
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def process_file(input_path: Path, out_f) -> int:
    count = 0
    with input_path.open() as f:
        lines = f.readlines()

    for line in tqdm(lines, desc=f"Extracting from {input_path.name}"):
        record = json.loads(line)
        text = record.get("text", "")
        if not text:
            continue

        chunks = chunk_text(text)
        for chunk in chunks:
            result = extract_triples(chunk)
            for triple in result.triples:
                out_record = {
                    **triple.model_dump(),
                    "source": record.get("source"),
                    "source_company": record.get("company_name"),
                    "source_date": record.get("filing_date") or record.get("seendate"),
                }
                out_f.write(json.dumps(out_record) + "\n")
                count += 1
    return count


def main():
    load_dotenv()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_path = PROCESSED_DIR / "triples.jsonl"

    input_files = [RAW_DIR / "sec_8k_filings.jsonl", RAW_DIR / "news_articles.jsonl"]
    input_files = [p for p in input_files if p.exists()]
    if not input_files:
        raise SystemExit("No raw data found. Run the ingestion scripts first (src/ingest/*.py).")

    total = 0
    with out_path.open("w") as out_f:
        for input_path in input_files:
            total += process_file(input_path, out_f)

    print(f"Wrote {total} triples to {out_path}")


if __name__ == "__main__":
    main()
