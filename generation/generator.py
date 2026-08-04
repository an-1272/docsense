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
    # No chunks returned at all
    if not chunks:
        return {
            'answer': 'I could not find a reliable answer to that in the provided documents.',
            'sources': [],
            'confidence': 'low'
        }
    # DEBUG — add these two lines temporarily
    #print(f"DEBUG: chunks[0] keys: {chunks[0].keys()}")
    #print(f"DEBUG: relevance_score = {chunks[0].get('relevance_score')}")
    #print(f"DEBUG: distance = {chunks[0].get('distance')}")

    # Use relevance_score if re-ranked, otherwise use distance
    if 'relevance_score' in chunks[0]:
        low_confidence = chunks[0]['relevance_score'] < 0.1
    else:
        low_confidence = chunks[0]['distance'] > CONFIDENCE_THRESHOLD

    if low_confidence:
        return {
            'answer': 'I could not find a reliable answer to that in the provided documents.',
            'sources': [],
            'confidence': 'low'
        }

    context = build_context(chunks)
    user_message = f'Context passages:\n{context}\n\nQuestion: {query}'
    # DEBUG
    #print(f"DEBUG context preview:\n{user_message[:1000]}")

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

    if 'relevance_score' in chunks[0]:
        confidence = 'high' if chunks[0]['relevance_score'] > 0.5 else 'medium'
    else:
        confidence = 'high' if chunks[0]['distance'] < 0.30 else 'medium'

    return {
        'answer': response.choices[0].message.content,
        'sources': sources,
        'confidence': confidence
    }

