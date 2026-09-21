# generation/graph.py
import os
import time
from typing import TypedDict, Optional
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END

load_dotenv()

USE_PINECONE = os.getenv('USE_PINECONE', 'false').lower() == 'true'
USE_AZURE_SEARCH = os.getenv('USE_AZURE_SEARCH', 'false').lower() == 'true'

MAX_RETRIES = 2


class GraphState(TypedDict):
    query: str
    search_query: str
    chunks: list
    critique: str
    sufficient: bool
    retry_count: int
    rerank_enabled: bool
    source_filter: Optional[list]
    n_results: int
    history: str
    result: Optional[dict]


def retrieve_node(state: GraphState) -> GraphState:
    search_query = state['search_query']
    source_filter = state['source_filter']
    rerank_enabled = state['rerank_enabled']
    n_results = state['n_results']

    if USE_AZURE_SEARCH:
        from retrieval.azure_search import search_azure, rerank_azure
        chunks = search_azure(search_query, n_results=20, source_filter=source_filter)
        if rerank_enabled:
            chunks = rerank_azure(search_query, chunks, top_n=n_results)
    elif USE_PINECONE:
        from retrieval.pinecone_search import search_pinecone, rerank_pinecone
        chunks = search_pinecone(search_query, n_results=20, source_filter=source_filter)
        if rerank_enabled:
            chunks = rerank_pinecone(search_query, chunks, top_n=n_results)
    else:
        from retrieval.search import search, rerank
        if rerank_enabled:
            chunks = search(search_query, n_results=20, source_filter=source_filter)
            chunks = rerank(search_query, chunks, top_n=n_results)
        else:
            chunks = search(search_query, n_results=n_results, source_filter=source_filter)

    return {**state, 'chunks': chunks}


def is_high_confidence(chunks: list) -> bool:
    """Same HIGH-confidence bar generate_answer() uses (see generation/generator.py)."""
    if not chunks:
        return False
    top = chunks[0]
    if 'relevance_score' in top:
        return top['relevance_score'] > 0.5
    return top['distance'] < 0.30


def should_critique(state: GraphState) -> str:
    # A retrieval that already clears the same HIGH-confidence bar the final
    # answer will be scored against doesn't need a second opinion — critique
    # is for genuinely borderline retrievals, not for second-guessing a
    # retrieval that's already demonstrably good.
    if is_high_confidence(state['chunks']):
        return 'respond'
    return 'critique'


def critique_node(state: GraphState) -> GraphState:
    from generation.critique import judge_sufficiency
    sufficient, reason = judge_sufficiency(state['query'], state['chunks'])
    return {**state, 'sufficient': sufficient, 'critique': reason}


def revise_node(state: GraphState) -> GraphState:
    from generation.critique import reformulate_query
    new_query = reformulate_query(state['query'], state['critique'])
    # A retry re-runs retrieve (and its rerank call) back-to-back with the
    # attempt that just ran — pace it so a revise loop can't burst past
    # Cohere's free-tier rate limit (10 calls/minute, see CLAUDE.md).
    time.sleep(2)
    return {**state, 'search_query': new_query, 'retry_count': state['retry_count'] + 1}


def respond_node(state: GraphState) -> GraphState:
    from generation.generator import generate_answer
    result = generate_answer(state['query'], state['chunks'], history=state['history'])
    result['rerank_enabled'] = state['rerank_enabled']
    return {**state, 'result': result}


def should_revise(state: GraphState) -> str:
    if state['sufficient'] or state['retry_count'] >= MAX_RETRIES:
        return 'respond'
    return 'revise'


builder = StateGraph(GraphState)
builder.add_node('retrieve', retrieve_node)
builder.add_node('critique', critique_node)
builder.add_node('revise', revise_node)
builder.add_node('respond', respond_node)

builder.set_entry_point('retrieve')
builder.add_conditional_edges('retrieve', should_critique, {'respond': 'respond', 'critique': 'critique'})
builder.add_conditional_edges('critique', should_revise, {'respond': 'respond', 'revise': 'revise'})
builder.add_edge('revise', 'retrieve')
builder.add_edge('respond', END)

compiled_graph = builder.compile()
