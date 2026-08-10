# pipeline.py — full updated file
from retrieval.search import search, rerank
from generation.generator import generate_answer
from generation.memory import get_history_string, add_turn, rewrite_query

def ask(query: str, n_results: int = 5, rerank_enabled: bool = True, memory=None) -> dict:
    
    # Rewrite follow-up queries using conversation history
    search_query = rewrite_query(query, memory) if memory else query

    if rerank_enabled:
        chunks = search(search_query, n_results=20)
        chunks = rerank(search_query, chunks, top_n=n_results)
    else:
        chunks = search(search_query, n_results=n_results)

    history = get_history_string(memory) if memory else ''
    result = generate_answer(query, chunks, history=history)
    result['rerank_enabled'] = rerank_enabled

    if memory and result['answer'] != 'I could not find a reliable answer to that in the provided documents.':
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
