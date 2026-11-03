# tests/test_azure_search_utils.py
import re
from retrieval.azure_search_utils import to_search_key, from_search_key, build_source_filter

AZURE_KEY_CHARS = re.compile(r'^[A-Za-z0-9_\-=]+$')


def test_key_is_valid_azure_key_for_real_chunk_ids():
    for cid in ['demo_corpus/The Honey Bee Apis mellifera - An Insect.pdf_p3_c0',
                'uploads/Attention Is All You Need.pdf_title',
                "uploads/Author's notes, v2.pdf_p1_c4"]:
        key = to_search_key(cid)
        assert AZURE_KEY_CHARS.match(key), key
        assert from_search_key(key) == cid


def test_key_is_deterministic():
    assert to_search_key('a/b.pdf_p1_c0') == to_search_key('a/b.pdf_p1_c0')


def test_filter_none_when_unscoped():
    assert build_source_filter(None) is None
    assert build_source_filter([]) is None


def test_filter_uses_pipe_delimiter():
    assert build_source_filter(['a.pdf', 'b, c.pdf']) == "search.in(source, 'a.pdf|b, c.pdf', '|')"


def test_filter_escapes_single_quotes():
    assert build_source_filter(["uploads/Author's notes.pdf"]) == "search.in(source, 'uploads/Author''s notes.pdf', '|')"
