from pipeline import ask, format_response
from generation.memory import create_memory

# ── A/B Test ────────────────────────────────────────────────
query = "What causes the green and blue colors in lightning flashes?"

print('=' * 60)
print('WITHOUT RE-RANKING (similarity search only)')
print('=' * 60)
result_base = ask(query, rerank_enabled=False)
print(format_response(result_base))

print()
print('=' * 60)
print('WITH RE-RANKING (Cohere Rerank)')
print('=' * 60)
result_reranked = ask(query, rerank_enabled=True)
print(format_response(result_reranked))

# ── Conversational Memory Test ───────────────────────────────
print()
print('=' * 60)
print('CONVERSATIONAL MEMORY TEST (re-ranking enabled)')
print('=' * 60)

memory = create_memory()

questions = [
    "What causes the green and blue colors in lightning flashes?",
    "Can you elaborate on the oxygen atom interaction?",
    "What else does the paper say about atmospheric factors?",
    "What is the capital of France?",
]

for i, q in enumerate(questions, 1):
    print(f"\n--- Turn {i} ---")
    print(f"Q: {q}")
    result = ask(q, rerank_enabled=True, memory=memory)
    print(format_response(result))