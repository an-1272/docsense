# deploy/create_search_index.py
"""
Creates (or updates) the Azure AI Search index DocSense expects.
Run from repo root:  python -m deploy.create_search_index
Reads AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_KEY / AZURE_SEARCH_INDEX from .env.

Fields mirror what ingestion/azure_search_embedder.py uploads and
retrieval/azure_search.py queries:
  id              key (base64url of chunk_id: Azure keys can't contain / . or spaces)
  text            searchable  -> keyword (BM25) half of hybrid search
  source          filterable  -> document scoping via search.in(source, ...)
  page            filterable
  content_vector  1536-dim (text-embedding-3-small), HNSW, cosine -> vector half
"""
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchableField, SearchField, SearchFieldDataType,
    VectorSearch, HnswAlgorithmConfiguration, HnswParameters, VectorSearchProfile,
)

load_dotenv()

INDEX_NAME = os.getenv('AZURE_SEARCH_INDEX', 'docsense')
EMBEDDING_DIMS = 1536


def build_index() -> SearchIndex:
    return SearchIndex(
        name=INDEX_NAME,
        fields=[
            SimpleField(name='id', type=SearchFieldDataType.String, key=True),
            SearchableField(name='text', type=SearchFieldDataType.String),
            SimpleField(name='source', type=SearchFieldDataType.String, filterable=True),
            SimpleField(name='page', type=SearchFieldDataType.Int32, filterable=True),
            SearchField(
                name='content_vector',
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=EMBEDDING_DIMS,
                vector_search_profile_name='docsense-hnsw-profile',
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(
                name='docsense-hnsw', parameters=HnswParameters(metric='cosine'))],
            profiles=[VectorSearchProfile(
                name='docsense-hnsw-profile', algorithm_configuration_name='docsense-hnsw')],
        ),
    )


if __name__ == '__main__':
    client = SearchIndexClient(
        endpoint=os.environ['AZURE_SEARCH_ENDPOINT'],
        credential=AzureKeyCredential(os.environ['AZURE_SEARCH_KEY']),
    )
    result = client.create_or_update_index(build_index())
    print(f'Index ready: {result.name} ({len(result.fields)} fields)')
