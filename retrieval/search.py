# retrieval/search.py
from ingestion.embedder import get_collection

def search(query: str, n_results: int = 5, collection_name: str = 'docsense') -> list[dict]:
    """
    Search ChromaDB for the top-n chunks most similar to the query.
    Returns a list of result dicts with text, source, page, and distance.
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
            'distance': results['distances'][0][i],   # lower = more similar
        })
    return output
