# ingestion/__init__.py
from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_pages
from ingestion.embedder import embed_chunks

def ingest(file_path: str):
    pages  = parse_pdf(file_path)
    chunks = chunk_pages(pages)
    embed_chunks(chunks)
    return len(chunks)
