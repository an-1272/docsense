from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_pages
from ingestion.embedder import embed_chunks

def ingest(file_path: str, source_name: str = None):
    """
    Ingest a document into ChromaDB.
    source_name: the display name to store as source metadata.
                 If not provided, uses the actual file path.
    """
    pages = parse_pdf(file_path)
    
    # Override source metadata with the display name if provided
    if source_name:
        for page in pages:
            page['source'] = source_name
    
    chunks = chunk_pages(pages)
    embed_chunks(chunks)
    return len(chunks)