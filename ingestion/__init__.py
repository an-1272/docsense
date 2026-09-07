# ingestion/__init__.py — updated
import os
from dotenv import load_dotenv
load_dotenv()

USE_PINECONE = os.getenv('USE_PINECONE', 'false').lower() == 'true'

from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_pages

def ingest(file_path: str, source_name: str = None):
    pages = parse_pdf(file_path)
    if source_name:
        for page in pages:
            page['source'] = source_name
    chunks = chunk_pages(pages)
    if USE_PINECONE:
        from ingestion.pinecone_embedder import embed_chunks_pinecone
        embed_chunks_pinecone(chunks)
    else:
        from ingestion.embedder import embed_chunks
        embed_chunks(chunks)
    return len(chunks)
