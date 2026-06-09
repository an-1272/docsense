from pipeline import ask, format_response

out_of_scope = [
    'Who won the World Cup in 2022?',
    'What is the boiling point of water?',
    'Write me a poem about the ocean.',
]

for q in out_of_scope:
    result = ask(q)
    print(f'Q: {q}')
    print(f'A: {result["answer"][:100]}')
    print(f'Confidence: {result["confidence"]}\n')
