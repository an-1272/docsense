# retrieval/scope_detect.py
"""
Query-time document scoping: infer which document(s) a question is about
from the question text itself, so the user doesn't have to use the
sidebar "Search scope" picker.

Deliberately deterministic (regex, no LLM call): it runs on every question,
must be free and instant, and must be predictable — a wrong auto-scope
silently hides the right document from retrieval, which is worse than not
scoping at all. So it only fires on unambiguous signals:

  1. The full filename appears in the question ("what does sample2.pdf say").
  2. The filename stem appears AND is distinctive — contains a digit or a
     separator ("HR2020", "biology-11-00233"), so it can't be an ordinary word.
  3. The filename stem appears immediately followed by a document noun
     ("the sample doc", "the report paper") — this lets plain-word stems
     match without "give me a sample of..." triggering a false scope.

The sidebar picker always wins: detection only runs when the picker is empty.
"""
import os
import re

DOC_NOUNS = r'(?:doc|docs|document|documents|pdf|file|paper|report|article)'


def _stem_pattern(stem: str) -> str:
    # Treat -, _, . and spaces in a filename as interchangeable, so
    # "biology-11-00233" also matches "biology 11 00233".
    parts = [re.escape(p) for p in re.split(r'[-_.\s]+', stem) if p]
    return r'[-_.\s]*'.join(parts)


def _is_distinctive(stem: str) -> bool:
    return bool(re.search(r'\d', stem) or re.search(r'[-_.]', stem))


def detect_sources(query: str, doc_sources: dict) -> list:
    """
    query:       the user's question
    doc_sources: display filename -> full `source` metadata value
                 (same mapping app.py keeps in st.session_state.doc_sources)

    Returns the list of `source` values named in the query, or [] if none.
    """
    if not query or not doc_sources:
        return []

    matched = []
    for display_name, source in doc_sources.items():
        stem = os.path.splitext(display_name)[0]
        if not stem:
            continue
        full = re.escape(display_name)
        stem_re = _stem_pattern(stem)

        patterns = [rf'(?<![\w]){full}(?![\w])']
        if _is_distinctive(stem):
            patterns.append(rf'(?<![\w]){stem_re}(?![\w])')
        patterns.append(rf'(?<![\w]){stem_re}\s+{DOC_NOUNS}\b')

        if any(re.search(p, query, flags=re.IGNORECASE) for p in patterns):
            matched.append(source)

    return matched
