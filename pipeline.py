# pipeline.py — full updated file
from retrieval.search import search, rerank
from generation.generator import generate_answer

def ask(query: str, n_results: int = 5, rerank_enabled: bool = True) -> dict:
    """
    Full RAG pipeline with optional re-ranking.
    rerank_enabled=True:  bi-encoder (top-20) → Cohere rerank → top-5 → LLM
    rerank_enabled=False: bi-encoder (top-5) → LLM  (original behaviour)
    """
    if rerank_enabled:
        chunks = search(query, n_results=20)   # wider net for re-ranker
        chunks = rerank(query, chunks, top_n=n_results)
    else:
        chunks = search(query, n_results=n_results)
    
    result = generate_answer(query, chunks)
    result['rerank_enabled'] = rerank_enabled
    return result

def format_response(result: dict) -> str:
    """Pretty-print the result for terminal testing."""
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
