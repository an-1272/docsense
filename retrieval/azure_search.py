# retrieval/azure_search.py
import os
import cohere
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from azure_client import get_openai_client, EMBEDDING_MODEL
from retrieval.azure_search_utils import build_source_filter

load_dotenv()

openai_client = get_openai_client()
co = cohere.Client(os.getenv('COHERE_API_KEY'))
search_client = SearchClient(
    endpoint=os.getenv('AZURE_SEARCH_ENDPOINT'),
    index_name=os.getenv('AZURE_SEARCH_INDEX', 'docsense'),
    credential=AzureKeyCredential(os.getenv('AZURE_SEARCH_KEY')),
)


def search_azure(query: str, n_results: int = 20, source_filter: list[str] = None) -> list[dict]:
    """Stage 1: hybrid search (vector + keyword) against Azure AI Search.
    Same return shape as retrieval/pinecone_search.py's search_pinecone(), and
    the same source_filter mechanism (Session 5 document scoping)."""
    response = openai_client.embeddings.create(
        input=[query],
        model=EMBEDDING_MODEL
    )
    vector_query = VectorizedQuery(
        vector=response.data[0].embedding,
        k_nearest_neighbors=n_results,
        fields='content_vector',
    )
    filter_expr = build_source_filter(source_filter)
    results = search_client.search(
        search_text=query,
        vector_queries=[vector_query],
        filter=filter_expr,
        select=['text', 'source', 'page'],
        top=n_results,
    )
    return [
        {
            'text': r['text'],
            'source': r['source'],
            'page': r['page'],
            'distance': 1 - r['@search.score'],
        }
        for r in results
    ]


def rerank_azure(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """Stage 2: re-rank candidates using Cohere — identical to rerank_pinecone()."""
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
