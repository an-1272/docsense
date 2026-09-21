# pipeline.py
from dotenv import load_dotenv
from langsmith import traceable

load_dotenv()

from generation.memory import get_history_string, add_turn, rewrite_query

@traceable(name='docsense_pipeline')
def ask(query: str, n_results: int = 5, rerank_enabled: bool = True, memory=None, source_filter: list[str] = None) -> dict:
    """
    Full RAG pipeline, run as a LangGraph state machine implementing the
    Reflection agent pattern: retrieve -> critique -> revise -> respond.
    A critique step judges whether retrieved chunks are actually sufficient
    to answer the query; if not, the query is reformulated and retrieval is
    retried (capped at graph.MAX_RETRIES) before an answer is generated.
    Routes to Pinecone or ChromaDB based on USE_PINECONE env variable.
    source_filter: if given (a list of `source` metadata values), restricts retrieval to those documents.
    """
    from generation.graph import compiled_graph

    search_query = rewrite_query(query, memory) if memory else query
    history = get_history_string(memory) if memory else ''

    final_state = compiled_graph.invoke({
        'query': query,
        'search_query': search_query,
        'chunks': [],
        'critique': '',
        'sufficient': False,
        'retry_count': 0,
        'rerank_enabled': rerank_enabled,
        'source_filter': source_filter,
        'n_results': n_results,
        'history': history,
        'result': None,
    })

    result = final_state['result']

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
            label = 'Document Summary' if s['page'] == 0 else f"Page {s['page']}"
            key = f"{source} — {label}"
            if key not in seen:
                output.append(f'  • {key}')
                seen.add(key)
    return '\n'.join(output)
