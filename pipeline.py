from retrieval.search import search
from generation.generator import generate_answer

def ask(query: str, n_results: int = 5) -> dict:
    """
    Full RAG pipeline: query -> retrieve -> generate -> return.
    Returns dict with answer, sources, and confidence.
    """
    chunks = search(query, n_results=n_results)
    result = generate_answer(query, chunks)
    return result

def format_response(result: dict) -> str:
    """Pretty-print the result for terminal testing."""
    output = []
    output.append(f'\nANSWER ({result["confidence"].upper()} confidence):')
    output.append('-' * 60)
    output.append(result['answer'])
    if result['sources']:
        output.append('\nSOURCES:')
        seen = set()
        for s in result['sources']:
            key = f"{s['source']} — Page {s['page']}"
            if key not in seen:
                output.append(f'  • {key}')
                seen.add(key)
    return '\n'.join(output)
