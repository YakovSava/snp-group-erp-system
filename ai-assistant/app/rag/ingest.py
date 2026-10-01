import hashlib
import re

from . import store

CHUNK_SIZE_CHARS = 800
CHUNK_OVERLAP_CHARS = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    buffer = ""
    for paragraph in paragraphs:
        if len(buffer) + len(paragraph) + 1 <= chunk_size:
            buffer = f"{buffer}\n{paragraph}".strip()
            continue
        if buffer:
            chunks.append(buffer)
        if len(paragraph) <= chunk_size:
            buffer = paragraph
        else:
            # A single paragraph longer than chunk_size: hard-split with overlap.
            start = 0
            while start < len(paragraph):
                chunks.append(paragraph[start : start + chunk_size])
                start += chunk_size - overlap
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def ingest_document(title: str, text: str) -> int:
    chunks = chunk_text(text)
    if not chunks:
        return 0
    ids = [hashlib.sha256(f"{title}:{i}:{chunk}".encode()).hexdigest() for i, chunk in enumerate(chunks)]
    metadatas = [{"title": title, "chunk_index": i} for i in range(len(chunks))]
    store.add_documents(ids=ids, texts=chunks, metadatas=metadatas)
    return len(chunks)
