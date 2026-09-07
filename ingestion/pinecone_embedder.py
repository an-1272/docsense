# ingestion/pinecone_embedder.py
from pinecone import Pinecone, ServerlessSpec
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
openai_client = OpenAI()
INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'docsense')

def get_index():
    return pc.Index(INDEX_NAME)

def embed_chunks_pinecone(chunks: list[dict]):
    """Embed chunks using OpenAI and upsert into Pinecone."""
    index = get_index()
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c['text'] for c in batch]
        response = openai_client.embeddings.create(
            input=texts,
            model='text-embedding-3-small'
        )
        vectors = []
        for j, c in enumerate(batch):
            vectors.append({
                'id': c['chunk_id'],
                'values': response.data[j].embedding,
                'metadata': {
                    'text': c['text'],
                    'source': c['source'],
                    'page': c['page']
                }
            })
        index.upsert(vectors=vectors)
    print(f'Embedded {len(chunks)} chunks into Pinecone index: {INDEX_NAME}')
