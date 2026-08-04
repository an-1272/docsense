# retrieval/search.py — full updated file
import cohere
import os
from dotenv import load_dotenv
from ingestion.embedder import get_collection

load_dotenv()
co = cohere.Client(os.getenv('COHERE_API_KEY'))

def search(query: str, n_results: int = 20, collection_name: str = 'docsense') -> list[dict]:
    """
    Stage 1: Bi-encoder similarity search.
    Retrieves top-n candidates by cosine distance.
    Default n increased to 20 to give re-ranker more candidates to work with.
    """
    collection = get_collection(collection_name)
    results = collection.query(
        query_texts=[query],
        n_results=n_results,
        include=['documents', 'metadatas', 'distances']
    )
    output = []
    for i in range(len(results['documents'][0])):
        output.append({
            'text':     results['documents'][0][i],
            'source':   results['metadatas'][0][i]['source'],
            'page':     results['metadatas'][0][i]['page'],
            'distance': results['distances'][0][i],
        })
    return output

def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Stage 2: Cross-encoder re-ranking via Cohere Rerank API.
    Takes top-20 candidates from search(), returns top-n by relevance score.
    """
    if not chunks:
        return []
    
    response = co.rerank(
        model='rerank-english-v3.0',
        query=query,
        documents=[c['text'] for c in chunks],
        top_n=top_n
    )
    
    reranked = []
    for result in response.results:
        chunk = chunks[result.index]
        reranked.append({
            'text':            chunk['text'],
            'source':          chunk['source'],
            'page':            chunk['page'],
            'distance':        chunk['distance'],
            'relevance_score': result.relevance_score,
        })
    return reranked
