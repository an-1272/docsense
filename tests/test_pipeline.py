# tests/test_pipeline.py
from ingestion.chunker import chunk_pages
from generation.context import build_context
from generation.memory import create_memory, add_turn, get_history_string


def test_chunker_returns_chunks():
    pages = [{'page': 1, 'text': 'A' * 1000, 'source': 'test.pdf'}]
    chunks = chunk_pages(pages)
    assert len(chunks) > 0
    assert all('text' in c for c in chunks)
    assert all('chunk_id' in c for c in chunks)


def test_chunker_attaches_metadata():
    pages = [{'page': 3, 'text': 'Sample text ' * 50, 'source': 'myfile.pdf'}]
    chunks = chunk_pages(pages)
    assert chunks[0]['source'] == 'myfile.pdf'
    assert chunks[0]['page'] == 3


def test_build_context_formats_correctly():
    chunks = [
        {'text': 'Hello world', 'source': 'test.pdf', 'page': 1},
        {'text': 'Second chunk', 'source': 'test.pdf', 'page': 2},
    ]
    context = build_context(chunks)
    assert 'Hello world' in context
    assert 'Page 1' in context


def test_memory_stores_and_retrieves_turns():
    memory = create_memory()
    add_turn(memory, 'Who wrote this?', 'Gilbert Green.')
    history = get_history_string(memory)
    assert 'Gilbert Green' in history


def test_memory_empty_on_init():
    memory = create_memory()
    history = get_history_string(memory)
    assert history == ''