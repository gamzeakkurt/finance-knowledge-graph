"""Thin wrapper around a local Ollama embedding model, used for semantic entity search."""

import os

import ollama

EMBEDDING_DIMENSIONS = 768


def get_embedding(text: str, model: str | None = None, host: str | None = None) -> list[float]:
    model = model or os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)
    response = client.embeddings(model=model, prompt=text)
    return response["embedding"]
