"""Quick CLI smoke test for semantic search.

Usage:
    python -m scripts.try_semantic_search "pharma company"
    python -m scripts.try_semantic_search "bank or financial institution" --k 10
"""

import argparse
import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

from src.graph.embeddings import get_embedding
from src.graph.queries import semantic_search_entities


def main():
    parser = argparse.ArgumentParser(description="Run a semantic search query against the entity graph.")
    parser.add_argument("query", help="Natural-language query, e.g. 'pharma company'")
    parser.add_argument("--k", type=int, default=10, help="Number of results to return (default: 10)")
    args = parser.parse_args()

    load_dotenv()
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "changeme")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        embedding = get_embedding(args.query)
        with driver.session() as session:
            results = semantic_search_entities(session, embedding, k=args.k)

        if not results:
            print("No results. Is the graph loaded and are entities embedded? See README.")
            return

        print(f'Top {len(results)} matches for "{args.query}":\n')
        for row in results:
            print(f"  {row['score']:.3f}  {row['name']}  ({row['type']})")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
