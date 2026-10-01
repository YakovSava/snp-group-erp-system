from functools import lru_cache

from sentence_transformers import SentenceTransformer

from ..config import get_settings


@lru_cache
def _model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model)


def embed_passages(texts: list[str]) -> list[list[float]]:
    """Embeds documents for storage. The E5 model family expects a
    "passage: " prefix on indexed text and a "query: " prefix on search
    queries — mixing them up quietly degrades retrieval quality.
    """
    prefixed = [f"passage: {text}" for text in texts]
    return _model().encode(prefixed, normalize_embeddings=True).tolist()


def embed_query(text: str) -> list[float]:
    return _model().encode([f"query: {text}"], normalize_embeddings=True).tolist()[0]
