# tests/test_scope_detect.py
from retrieval.scope_detect import detect_sources

DOCS = {
    'sample.pdf': 'demo_corpus/sample.pdf',
    'sample2.pdf': 'demo_corpus/sample2.pdf',
    'biology-11-00233.pdf': 'uploads/biology-11-00233.pdf',
    'HR2020.pdf': 'uploads/HR2020.pdf',
}


def test_full_filename_matches():
    assert detect_sources('What does sample.pdf say about storms?', DOCS) == ['demo_corpus/sample.pdf']


def test_similar_names_do_not_cross_match():
    assert detect_sources('Summarise sample2.pdf', DOCS) == ['demo_corpus/sample2.pdf']


def test_distinctive_stem_matches_without_extension():
    assert detect_sources('what does the HR2020 policy cover', DOCS) == ['uploads/HR2020.pdf']


def test_separators_are_interchangeable():
    assert detect_sources('key findings in biology 11 00233?', DOCS) == ['uploads/biology-11-00233.pdf']


def test_plain_word_stem_needs_doc_noun():
    # "sample" is an ordinary English word — must not scope on its own
    assert detect_sources('give me a sample of the results', DOCS) == []
    assert detect_sources('what is the sample doc about', DOCS) == ['demo_corpus/sample.pdf']


def test_multiple_documents():
    result = detect_sources('compare sample.pdf with HR2020', DOCS)
    assert set(result) == {'demo_corpus/sample.pdf', 'uploads/HR2020.pdf'}


def test_no_match_and_empty_inputs():
    assert detect_sources('who are the authors?', DOCS) == []
    assert detect_sources('', DOCS) == []
    assert detect_sources('sample.pdf', {}) == []
