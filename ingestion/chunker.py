# ingestion/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_pages(pages: list[dict], chunk_size=1000, chunk_overlap=200) -> list[dict]:
    """
    Takes parsed page dicts, returns a flat list of chunk dicts.
    Each chunk: { 'text': str, 'source': str, 'page': int, 'chunk_id': str }
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunks = []
    for page in pages:
        splits = splitter.split_text(page['text'])
        for i, split in enumerate(splits):
            chunks.append({
                'text': split,
                'source': page['source'],
                'page': page['page'],
                'chunk_id': f"{page['source']}_p{page['page']}_c{i}"
            })
    return chunks
