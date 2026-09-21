# generation/critique.py
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()


def judge_sufficiency(query: str, chunks: list[dict]) -> tuple[bool, str]:
    """
    Reflection step: asks whether the retrieved chunks actually contain
    enough information to answer the query. Returns (sufficient, reason).
    """
    if not chunks:
        return False, 'No chunks were retrieved.'

    context = '\n\n'.join(f'[{i+1}] {c["text"]}' for i, c in enumerate(chunks))
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=150,
        messages=[
            {
                'role': 'system',
                'content': (
                    'You judge whether retrieved passages contain enough information '
                    'to answer a question. Respond in exactly this format:\n'
                    'Sufficient: yes|no\n'
                    'Reason: <one sentence>'
                )
            },
            {'role': 'user', 'content': f'Question: {query}\n\nRetrieved passages:\n{context}'}
        ]
    )
    body = response.choices[0].message.content.strip()
    sufficient = 'sufficient: yes' in body.lower()
    reason_line = next((line for line in body.split('\n') if line.lower().startswith('reason:')), '')
    reason = reason_line.split(':', 1)[1].strip() if ':' in reason_line else body
    return sufficient, reason


def reformulate_query(query: str, critique: str) -> str:
    """
    Rewrites the query into a better search query, given why the previous
    retrieval was judged insufficient.
    """
    response = client.chat.completions.create(
        model='gpt-4o-mini',
        max_tokens=60,
        messages=[
            {
                'role': 'system',
                'content': (
                    'Rewrite the question into a better search query for a document '
                    'retrieval system, given why the previous retrieval fell short. '
                    'Respond with ONLY the rewritten query, no explanation.'
                )
            },
            {'role': 'user', 'content': f'Original question: {query}\nWhy retrieval fell short: {critique}'}
        ]
    )
    return response.choices[0].message.content.strip()
