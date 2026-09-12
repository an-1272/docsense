# ingestion/title_chunk.py
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def generate_title_chunk(pages: list[dict], source: str) -> dict:
    """
    Synthesizes one extra chunk per document that answers identity/topic
    questions ("what is this document about", "what does the X doc say")
    that raw content chunks are poorly matched to.
    """
    filename = source.replace('\\', '/').split('/')[-1]
    lead_text = pages[0]['text'][:3000] if pages else ''

    response = client.chat.completions.create(
        model='gpt-4o-mini',
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

    text = f'Document filename: {filename}\n{body}'

    return {
        'text': text,
        'source': source,
        'page': 0,
        'chunk_id': f'{source}_title',
        'chunk_type': 'title',
    }
