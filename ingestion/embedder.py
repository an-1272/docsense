import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
import os

load_dotenv()

def get_collection(collection_name: str = 'docsense'):
    """Return (or create) a ChromaDB collection with OpenAI embeddings."""
    client = chromadb.PersistentClient(path='./db')
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.getenv('OPENAI_API_KEY'),
        model_name='text-embedding-3-small'
    )
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=openai_ef
    )

def embed_chunks(chunks: list[dict], collection_name: str = 'docsense'):
    """Embed all chunks and upsert into ChromaDB."""
    collection = get_collection(collection_name)
    collection.upsert(
        documents=[c['text'] for c in chunks],
        ids=[c['chunk_id'] for c in chunks],
        metadatas=[{
            'source': c['source'],
            'page': c['page']
        } for c in chunks]
    )
    print(f'Embedded {len(chunks)} chunks into collection: {collection_name}')
