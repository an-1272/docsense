# ingestion/azure_search_embedder.py
import os
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from dotenv import load_dotenv
from azure_client import get_openai_client, EMBEDDING_MODEL

load_dotenv()

INDEX_NAME = os.getenv('AZURE_SEARCH_INDEX', 'docsense')
openai_client = get_openai_client()
search_client = SearchClient(
    endpoint=os.getenv('AZURE_SEARCH_ENDPOINT'),
    index_name=INDEX_NAME,
    credential=AzureKeyCredential(os.getenv('AZURE_SEARCH_KEY')),
)


def embed_chunks_azure_search(chunks: list[dict]):
    """Embed chunks using (Azure) OpenAI and upload into the Azure AI Search index.
    Same chunk_id/source/page shape as ingestion/pinecone_embedder.py, so a
    corpus ingested for Pinecone re-ingests identically here."""
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c['text'] for c in batch]
        response = openai_client.embeddings.create(
            input=texts,
            model=EMBEDDING_MODEL
        )
        docs = []
        for j, c in enumerate(batch):
            docs.append({
                'id': c['chunk_id'],
                'text': c['text'],
                'source': c['source'],
                'page': c['page'],
                'content_vector': response.data[j].embedding,
            })
        search_client.upload_documents(documents=docs)
    print(f'Embedded {len(chunks)} chunks into Azure AI Search index: {INDEX_NAME}')
