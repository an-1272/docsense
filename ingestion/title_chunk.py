# ingestion/title_chunk.py
from dotenv import load_dotenv
from azure_client import get_openai_client, CHAT_MODEL

load_dotenv()
client = get_openai_client()


def generate_title_chunk(pages: list[dict], source: str) -> dict:
    """
    Synthesizes one extra chunk per document that answers identity/topic
    questions ("what is this document about", "what does the X doc say")
    that raw content chunks are poorly matched to.
    """
    filename = source.replace('\\', '/').split('/')[-1]
    lead_text = pages[0]['text'][:3000] if pages else ''

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        max_tokens=150,
        messages=[
            {
                'role': 'system',
                'content': (
                    'Given the opening text of a document, respond in exactly this format:\n'
                    'Title: <the document\'s actual title, or a short descriptive title if none is stated>\n'
                    'Summary: <one-sentence summary of what the document is about>'
                )
            },
            {'role': 'user', 'content': lead_text}
        ]
    )
    body = response.choices[0].message.content.strip()

    text = compose_title_text(filename, body)

    return {
        'text': text,
        'source': source,
        'page': 0,
        'chunk_id': f'{source}_title',
        'chunk_type': 'title',
    }


def compose_title_text(filename: str, model_output: str) -> str:
    """
    Turns the model's "Title: ... / Summary: ..." output into one plain-prose
    sentence, e.g. 'What this document is about: the paper "X" (file x.pdf) is about Y. Its main topic is X.'

    Why prose and not the labelled format: the Cohere cross-encoder reranker scores
    how well a passage *reads as an answer* to the question. A labelled metadata list
    ("Document filename: / Title: / Summary:") scored 0.001 for "What is the main topic
    of the paper?" — so the chunk built for exactly that question was reranked to #15
    and the query fell back to "not found". The same content as prose scores ~0.92+.
    """
    title, summary = '', ''
    for line in model_output.splitlines():
        line = line.strip()
        if line.lower().startswith('title:'):
            title = line[len('title:'):].strip()
        elif line.lower().startswith('summary:'):
            summary = line[len('summary:'):].strip()

    if not (title and summary):
        # Model didn't follow the format — keep its text rather than lose the chunk.
        return f'This document (file {filename}) is described as follows: {model_output.strip()}'

    summary_clause = summary[0].lower() + summary[1:]
    stripped = False
    for lead in ('this article ', 'this paper ', 'this document ', 'this study ', 'this review ',
                 'the article ', 'the paper ', 'the document ', 'the study ', 'the review '):
        if summary_clause.startswith(lead):
            summary_clause = summary_clause[len(lead):]   # "reports on ..." — a verb phrase
            stripped = True
            break
    if not stripped:
        summary_clause = f'is about {summary_clause}'     # "a study of ..." — a noun phrase
    summary_clause = summary_clause.rstrip('.')
    # Wording chosen by measured rerank score (Cohere rerank-english-v3.0) across
    # "main topic of the paper" / "this document about" / "the paper about" /
    # "what does <file> say": >= 0.92 on all four. A "This paper, titled ..." variant
    # dropped "What is this document about?" to 0.20 — the reranker keys on doc/paper wording.
    return (
        f'What this document is about: the paper "{title}" (file {filename}) {summary_clause}. '
        f'Its main topic is {title}.'
    )
