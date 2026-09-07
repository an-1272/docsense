# retrieval/pinecone_search.py
from pinecone import Pinecone
from openai import OpenAI
import cohere
import os
from dotenv import load_dotenv

load_dotenv()

pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
openai_client = OpenAI()
co = cohere.Client(os.getenv('COHERE_API_KEY'))
INDEX_NAME = os.getenv('PINECONE_INDEX_NAME', 'docsense')

def search_pinecone(query: str, n_results: int = 20) -> list[dict]:
    """Stage 1: Embed query and search Pinecone for top-n candidates."""
    index = pc.Index(INDEX_NAME)
    response = openai_client.embeddings.create(
        input=[query],
        model='text-embedding-3-small'
    )
    query_vector = response.data[0].embedding
    results = index.query(
        vector=query_vector,
        top_k=n_results,
        include_metadata=True
    )
    return [
        {
            'text':     match.metadata['text'],
            'source':   match.metadata['source'],
            'page':     match.metadata['page'],
            'distance': 1 - match.score,  # convert similarity to distance
        }
        for match in results.matches
    ]

def rerank_pinecone(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """Stage 2: Re-rank candidates using Cohere cross-encoder."""
    if not chunks:
        return []
    response = co.rerank(
        model='rerank-english-v3.0',
        query=query,
        documents=[c['text'] for c in chunks],
        top_n=top_n
    )
    return [
        {**chunks[r.index], 'relevance_score': r.relevance_score}
        for r in response.results
    ]
