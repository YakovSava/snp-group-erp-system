from functools import lru_cache

import chromadb

from ..config import get_settings
from .embeddings import embed_passages, embed_query

COLLECTION_NAME = "company_knowledge"


@lru_cache
def _client():
    settings = get_settings()
    # anonymized_telemetry=False: Chroma's own analytics call errors on this
    # chromadb/posthog version pairing ("capture() takes 1 positional
    # argument but 3 were given") — harmless but noisy on every query/insert.
    return chromadb.PersistentClient(
        path=settings.chroma_path,
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


def _collection():
    # We supply our own (E5, prefix-aware) embeddings on every call, so the
    # collection is created with no embedding function of its own. Explicit
    # cosine space so returned `distances` are a predictable 0 (identical)
    # .. 2 (opposite) range regardless of Chroma's default (L2).
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(ids: list[str], texts: list[str], metadatas: list[dict]) -> None:
    embeddings = embed_passages(texts)
    _collection().add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)


def query(text: str, n_results: int = 4) -> list[dict]:
    embedding = embed_query(text)
    result = _collection().query(query_embeddings=[embedding], n_results=n_results)
    hits = []
    documents = result.get("documents") or [[]]
    metadatas = result.get("metadatas") or [[]]
    distances = result.get("distances") or [[]]
    for doc, meta, distance in zip(documents[0], metadatas[0], distances[0]):
        hits.append({"text": doc, "metadata": meta, "distance": distance})
    return hits
