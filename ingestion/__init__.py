# ingestion/__init__.py — updated
import os
from dotenv import load_dotenv
load_dotenv()

USE_PINECONE = os.getenv('USE_PINECONE', 'false').lower() == 'true'
USE_AZURE_SEARCH = os.getenv('USE_AZURE_SEARCH', 'false').lower() == 'true'

from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_pages
from ingestion.title_chunk import generate_title_chunk

def ingest(file_path: str, source_name: str = None):
    pages = parse_pdf(file_path)
    if source_name:
        for page in pages:
            page['source'] = source_name
    source = source_name or file_path
    chunks = chunk_pages(pages)
    chunks.insert(0, generate_title_chunk(pages, source))
    # Same precedence as generation/graph.py's retrieve_node — ingestion and retrieval
    # must route to the SAME store, or every answer comes back "not found".
    if USE_AZURE_SEARCH:
        from ingestion.azure_search_embedder import embed_chunks_azure_search
        embed_chunks_azure_search(chunks)
    elif USE_PINECONE:
        from ingestion.pinecone_embedder import embed_chunks_pinecone
        embed_chunks_pinecone(chunks)
    else:
        from ingestion.embedder import embed_chunks
        embed_chunks(chunks)
    return len(chunks)
