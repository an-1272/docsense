from openai import OpenAI
from dotenv import load_dotenv
from generation.prompts import SYSTEM_PROMPT
from generation.context import build_context

load_dotenv()
client = OpenAI()

CONFIDENCE_THRESHOLD = 0.45

def generate_answer(query: str, chunks: list[dict]) -> dict:
    """
    Generate a grounded, cited answer from retrieved chunks.
    Returns a dict with 'answer', 'sources', and 'confidence'.
    """
    # Check confidence — if best match is too weak, fire fallback
    if not chunks or chunks[0]['distance'] > CONFIDENCE_THRESHOLD:
        return {
            'answer': 'I could not find a reliable answer to that in the provided documents.',
            'sources': [],
            'confidence': 'low'
        }

    context = build_context(chunks)
    user_message = f'Context passages:\n{context}\n\nQuestion: {query}'

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=1024,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message}
        ]
    )

    sources = [
        {'source': c['source'], 'page': c['page']}
        for c in chunks
    ]

    return {
        'answer': response.choices[0].message.content,
        'sources': sources,
        'confidence': 'high' if chunks[0]['distance'] < 0.30 else 'medium'
    }
