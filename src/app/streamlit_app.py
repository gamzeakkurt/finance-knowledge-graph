"""Streamlit app: search an entity, view its interactive neighborhood graph."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st
from dotenv import load_dotenv
from neo4j import GraphDatabase
from pyvis.network import Network

from src.graph.embeddings import get_embedding
from src.graph.queries import (
    get_graph_stats,
    get_neighborhood,
    get_top_connected,
    search_entities,
    semantic_search_entities,
)

load_dotenv()

st.set_page_config(page_title="Finance Knowledge Graph", layout="wide")


@st.cache_resource
def get_driver():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "changeme")
    return GraphDatabase.driver(uri, auth=(user, password))


def render_neighborhood(rows, center_name: str) -> str:
    net = Network(height="600px", width="100%", directed=True, notebook=False)
    seen_nodes = set()

    def add_node(name, node_type):
        if name in seen_nodes:
            return
        color = "#4C9AFF" if node_type == "Company" else "#FF8B00"
        size = 30 if name == center_name else 18
        net.add_node(name, label=name, color=color, size=size)
        seen_nodes.add(name)

    for row in rows:
        add_node(row["source"], row["source_type"])
        add_node(row["target"], row["target_type"])
        net.add_edge(row["source"], row["target"], label=row["relation"], arrows="to")

    net.repulsion(node_distance=180, spring_length=180)
    out_path = "/tmp/kg_graph.html"
    net.write_html(out_path, open_browser=False, notebook=False)
    with open(out_path) as f:
        return f.read()


def main():
    st.title("Finance Knowledge Graph")
    st.caption("S&P 500 M&A activity and executive leadership changes, extracted from SEC 8-K filings and news.")

    driver = get_driver()

    with driver.session() as session:
        stats = get_graph_stats(session)
        col1, col2 = st.columns(2)
        col1.metric("Entities", stats["node_count"])
        col2.metric("Relationships", stats["edge_count"])

        st.sidebar.header("Most connected entities")
        top = get_top_connected(session, limit=10)
        for row in top:
            st.sidebar.write(f"**{row['name']}** ({row['type']}) — {row['degree']} connections")

        query = st.text_input("Search for a company or person")

        selected_entity = None
        if query:
            matches = search_entities(session, query)
            if matches:
                options = [f"{m['name']} ({m['type']})" for m in matches]
                choice = st.selectbox("Matches", options)
                selected_entity = matches[options.index(choice)]["name"]
            else:
                st.warning("No matches found.")

        with st.expander("Semantic search"):
            st.caption("Search by meaning instead of exact name, e.g. \"pharma company\" or \"recent leadership change\".")
            semantic_query = st.text_input("Describe what you're looking for", key="semantic_query")
            if semantic_query:
                query_embedding = get_embedding(semantic_query)
                semantic_matches = semantic_search_entities(session, query_embedding, k=10)
                if semantic_matches:
                    semantic_options = [
                        f"{m['name']} ({m['type']}) — similarity {m['score']:.2f}" for m in semantic_matches
                    ]
                    semantic_choice = st.selectbox("Semantic matches", semantic_options, key="semantic_choice")
                    idx = semantic_options.index(semantic_choice)
                    selected_entity = semantic_matches[idx]["name"]
                else:
                    st.warning("No semantic matches found.")

        if selected_entity:
            hop_limit = st.slider("Max neighbors shown", 10, 200, 50)
            rows = get_neighborhood(session, selected_entity, limit=hop_limit)
            if rows:
                html = render_neighborhood(rows, selected_entity)
                st.components.v1.html(html, height=620)
            else:
                st.info("No relationships found for this entity.")


if __name__ == "__main__":
    main()
