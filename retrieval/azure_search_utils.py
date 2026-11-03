# retrieval/azure_search_utils.py
"""
Pure helpers for the Azure AI Search backend (no client, no credentials), so they
can be unit-tested in CI.
"""
import base64


def to_search_key(chunk_id: str) -> str:
    """
    Azure AI Search document keys may only contain letters, digits, '_', '-' and '='.
    Our chunk_ids are built from source paths ("demo_corpus/The Honey Bee ... .pdf_p3_c0"),
    so slashes, dots and spaces would make every upload fail. URL-safe base64 maps any
    string to that alphabet, is deterministic (re-ingesting overwrites the same document,
    same as Pinecone upserts) and is reversible for debugging.
    """
    return base64.urlsafe_b64encode(chunk_id.encode('utf-8')).decode('ascii')


def from_search_key(key: str) -> str:
    return base64.urlsafe_b64decode(key.encode('ascii')).decode('utf-8')


def build_source_filter(source_filter: list[str] | None) -> str | None:
    """
    OData filter restricting results to the given `source` values.
    search.in() takes the delimiter as its 3rd argument; '|' is used instead of ','
    so a filename containing a comma isn't split in two. Single quotes are doubled
    (OData string escaping), otherwise a filename like "Author's notes.pdf" would end
    the string literal early and break the query.
    """
    if not source_filter:
        return None
    values = '|'.join(s.replace("'", "''") for s in source_filter)
    return f"search.in(source, '{values}', '|')"
