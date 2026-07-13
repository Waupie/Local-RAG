"""
Topical guardrail based on what's actually been ingested into the vector
store, rather than a hardcoded topic list.

Cheap, no LLM call: rejects queries that aren't close to anything in the
corpus based on embedding similarity.

get_embedding_fn / search_fn are injected (your existing blocking
requests/psycopg2 calls) so this file has no dependency on app.py.
"""
import asyncio
from typing import Callable, List, Tuple

SimilarityMatch = Tuple[str, float]  # (content, similarity)


async def similarity_guardrail(
    query: str,
    get_embedding_fn: Callable[[str], List[float]],
    search_fn: Callable[[List[float], int], List[SimilarityMatch]],
    top_k: int = 3,
    threshold: float = 0.4,
) -> Tuple[bool, float, List[SimilarityMatch]]:
    """
    Returns (allowed, best_similarity, matches).
    Runs the blocking embedding/search calls in a thread so this stays
    awaitable without rewriting your DB/Ollama code as async.
    """
    embedding = await asyncio.to_thread(get_embedding_fn, query)
    matches = await asyncio.to_thread(search_fn, embedding, top_k)

    if not matches:
        return False, 0.0, []

    best_similarity = max(sim for _, sim in matches)
    return best_similarity >= threshold, best_similarity, matches