from pipeline import ask, format_response

# Use a query that previously gave weak results
query = "What causes the green and blue colors observed in the lightning flashes?"

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