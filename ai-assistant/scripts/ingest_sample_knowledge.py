"""Seeds the local Chroma knowledge base from plain-text files.

Usage (from inside the api container or a matching local env):
    python scripts/ingest_sample_knowledge.py path/to/doc1.txt path/to/doc2.txt

For non-text files (pdf/docx/xlsx/pptx), extract text first with
app.files.extract.extract_text and feed the result to ingest_document, or
POST directly to /v1/knowledge/documents with the extracted text.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.rag.ingest import ingest_document  # noqa: E402


def main(paths: list[str]) -> None:
    for path_str in paths:
        path = pathlib.Path(path_str)
        text = path.read_text(encoding="utf-8")
        count = ingest_document(title=path.stem, text=text)
        print(f"{path.name}: ingested {count} chunks")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    main(sys.argv[1:])
