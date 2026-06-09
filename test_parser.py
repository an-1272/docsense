from ingestion.parser import parse_pdf
from ingestion.chunker import chunk_pages
pages = parse_pdf("demo_corpus/sample.pdf")
chunks = chunk_pages(pages)
print(f'Total chunks: {len(chunks)}')
print(f'First chunk ({len(chunks[0]["text"])} chars):')
print(chunks[0]['text'])
