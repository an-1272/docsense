# tests/test_title_chunk.py
from ingestion.title_chunk import compose_title_text


def test_verb_phrase_summary_reads_as_prose():
    out = compose_title_text('sample.pdf', 'Title: Green Flashes\nSummary: This article reports on coloured lightning.')
    assert out == 'What this document is about: the paper "Green Flashes" (file sample.pdf) reports on coloured lightning. Its main topic is Green Flashes.'


def test_noun_phrase_summary_gets_is_about():
    out = compose_title_text('b.pdf', 'Title: Bees\nSummary: A review of honey bee health.')
    assert out == 'What this document is about: the paper "Bees" (file b.pdf) is about a review of honey bee health. Its main topic is Bees.'


def test_no_labelled_metadata_format():
    # The labelled format is what the reranker scored ~0.001 for "main topic" questions.
    out = compose_title_text('x.pdf', 'Title: T\nSummary: This paper studies S.')
    assert 'Document filename:' not in out and 'Title:' not in out and 'Summary:' not in out


def test_unformatted_model_output_is_kept():
    out = compose_title_text('x.pdf', 'free text with no labels')
    assert 'x.pdf' in out and 'free text with no labels' in out
