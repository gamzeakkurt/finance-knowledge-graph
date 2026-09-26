"""Load validated triples from JSONL into Neo4j via MERGE (idempotent upsert)."""

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from neo4j import GraphDatabase
from tqdm import tqdm

from src.graph.embeddings import EMBEDDING_DIMENSIONS, get_embedding

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"

COMPANY_SUFFIXES = re.compile(
    r"\b(Inc\.?|Corp\.?|Corporation|Co\.?|Company|Ltd\.?|LLC|L\.L\.C\.|plc|PLC)\b\.?\s*$",
    re.IGNORECASE,
)

# Every node also gets the shared :Entity label so a single vector index
# can cover both Company and Person nodes (Neo4j doesn't support multi-label
# vector indexes, e.g. `FOR (n:Company|Person)`).
MERGE_QUERY = """
MERGE (s:{subject_label}:Entity {{name: $subject}})
MERGE (o:{object_label}:Entity {{name: $object}})
MERGE (s)-[r:{relation}]->(o)
ON CREATE SET r.source = $source, r.source_date = $source_date
"""

VECTOR_INDEX_QUERY = f"""
CREATE VECTOR INDEX entity_embeddings IF NOT EXISTS
FOR (n:Entity) ON (n.embedding)
OPTIONS {{indexConfig: {{
  `vector.dimensions`: {EMBEDDING_DIMENSIONS},
  `vector.similarity_function`: 'cosine'
}}}}
"""

UNEMBEDDED_ENTITIES_QUERY = """
MATCH (n:Entity)
WHERE n.embedding IS NULL
RETURN n.name AS name
"""

SET_EMBEDDING_QUERY = """
MATCH (n:Entity {name: $name})
SET n.embedding = $embedding
"""


def normalize_name(name: str) -> str:
    """Basic normalization to reduce duplicate nodes: trim, collapse whitespace, strip common suffixes."""
    name = " ".join(name.split())
    stripped = COMPANY_SUFFIXES.sub("", name).strip()
    return stripped or name


def ensure_vector_index(driver) -> None:
    with driver.session() as session:
        session.run(VECTOR_INDEX_QUERY)


def embed_missing_entities(driver) -> int:
    """Embed any :Entity node that doesn't already have an embedding (covers fresh loads and backfills)."""
    with driver.session() as session:
        names = [row["name"] for row in session.run(UNEMBEDDED_ENTITIES_QUERY).data()]

    for name in tqdm(names, desc="Embedding entities"):
        embedding = get_embedding(name)
        with driver.session() as session:
            session.run(SET_EMBEDDING_QUERY, {"name": name, "embedding": embedding})

    return len(names)


def load_triples(driver, triples_path: Path) -> int:
    count = 0
    with driver.session() as session, triples_path.open() as f:
        lines = f.readlines()
        for line in tqdm(lines, desc="Loading triples into Neo4j"):
            record = json.loads(line)
            subject = normalize_name(record["subject"])
            obj = normalize_name(record["object"])

            query = MERGE_QUERY.format(
                subject_label=record["subject_type"],
                object_label=record["object_type"],
                relation=record["relation"],
            )
            session.run(
                query,
                subject=subject,
                object=obj,
                source=record.get("source"),
                source_date=record.get("source_date"),
            )
            count += 1
    return count


def main():
    load_dotenv()
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "changeme")

    triples_path = PROCESSED_DIR / "triples.jsonl"
    if not triples_path.exists():
        raise SystemExit("No triples found. Run src/extraction/extract.py first.")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        driver.verify_connectivity()
        ensure_vector_index(driver)
        count = load_triples(driver, triples_path)
        print(f"Loaded {count} triples into Neo4j at {uri}")
        embedded_count = embed_missing_entities(driver)
        print(f"Embedded {embedded_count} entities for semantic search")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
