# generation/generator.py — updated generate_answer() signature and prompt
from openai import OpenAI
from dotenv import load_dotenv
from generation.prompts import SYSTEM_PROMPT
from generation.context import build_context
from langsmith import traceable

load_dotenv()
client = OpenAI()

CONFIDENCE_THRESHOLD = 0.45

@traceable(name='generate_answer')
def generate_answer(query: str, chunks: list[dict], history: str = '') -> dict:
    """
    Generate a grounded, cited answer from retrieved chunks.
    Accepts optional conversation history string for multi-turn support.
    """
    if not chunks:
        return {
            'answer': 'I could not find a reliable answer to that in the provided documents.',
            'sources': [],
            'confidence': 'low'
        }

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

    # Build user message — include history if available
    if history:
        user_message = (
            f'Previous conversation:\n{history}\n\n'
            f'Context passages:\n{context}\n\n'
            f'Question: {query}'
        )
    else:
        user_message = f'Context passages:\n{context}\n\nQuestion: {query}'

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=1024,
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': user_message}
        ]
    )

    sources = [{'source': c['source'], 'page': c['page']} for c in chunks]

    if 'relevance_score' in chunks[0]:
        confidence = 'high' if chunks[0]['relevance_score'] > 0.5 else 'medium'
    else:
        confidence = 'high' if chunks[0]['distance'] < 0.30 else 'medium'

    return {
        'answer': response.choices[0].message.content,
        'sources': sources,
        'confidence': confidence
    }
