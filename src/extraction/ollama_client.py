"""Thin wrapper around a local Ollama server: prompt, parse JSON, validate, retry."""

import json
import logging
import os
import re

import ollama
from pydantic import ValidationError

from src.extraction.prompts import SYSTEM_PROMPT, build_user_prompt
from src.extraction.schema import ExtractionResult

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _extract_json_block(raw: str) -> str:
    """Local models sometimes wrap JSON in markdown fences or add stray text - strip that."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        return fenced.group(1)
    brace_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if brace_match:
        return brace_match.group(0)
    return raw


def extract_triples(text: str, model: str | None = None, host: str | None = None) -> ExtractionResult:
    """Call the local LLM and return a validated ExtractionResult, retrying on bad output."""
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.1:8b")
    host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    client = ollama.Client(host=host)

    user_prompt = build_user_prompt(text)

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                options={"temperature": 0.0},
            )
            raw_content = response["message"]["content"]
            json_str = _extract_json_block(raw_content)
            parsed = json.loads(json_str)
            return ExtractionResult.model_validate(parsed)
        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            last_error = e
            logger.warning("Extraction attempt %d/%d failed: %s", attempt, MAX_RETRIES, e)

    logger.error("All %d extraction attempts failed, returning empty result. Last error: %s", MAX_RETRIES, last_error)
    return ExtractionResult(triples=[])
