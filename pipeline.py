# pipeline.py
import os
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

USE_PINECONE = os.getenv('USE_PINECONE', 'false').lower() == 'true'

from generation.generator import generate_answer
from generation.memory import get_history_string, add_turn, rewrite_query

@traceable(name='docsense_pipeline')
def ask(query: str, n_results: int = 5, rerank_enabled: bool = True, memory=None) -> dict:
    """
    Full RAG pipeline with optional re-ranking.
    Routes to Pinecone or ChromaDB based on USE_PINECONE env variable.
    """
    search_query = rewrite_query(query, memory) if memory else query

    if USE_PINECONE:
        from retrieval.pinecone_search import search_pinecone, rerank_pinecone
        chunks = search_pinecone(search_query, n_results=20)
        if rerank_enabled:
            chunks = rerank_pinecone(search_query, chunks, top_n=n_results)
    else:
        from retrieval.search import search, rerank
        if rerank_enabled:
            chunks = search(search_query, n_results=20)
            chunks = rerank(search_query, chunks, top_n=n_results)
        else:
            chunks = search(search_query, n_results=n_results)

    history = get_history_string(memory) if memory else ''
    result = generate_answer(query, chunks, history=history)
    result['rerank_enabled'] = rerank_enabled

    if memory and 'could not find' not in result['answer'].lower():
        add_turn(memory, query, result['answer'])

    return result

def format_response(result: dict) -> str:
    mode = 'RE-RANKED' if result.get('rerank_enabled') else 'SIMILARITY ONLY'
    output = []
    output.append(f'\nANSWER ({result["confidence"].upper()} confidence | {mode}):')
    output.append('-' * 60)
    output.append(result['answer'])
    if result['sources']:
        output.append('\nSOURCES:')
        seen = set()
        for s in result['sources']:
            source = s['source'].replace('\\', '/')
            if 'Temp' in source or 'tmp' in source.lower():
                continue
            key = f"{source} — Page {s['page']}"
            if key not in seen:
                output.append(f'  • {key}')
                seen.add(key)
    return '\n'.join(output)