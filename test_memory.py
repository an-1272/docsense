# test_memory.py
from pipeline import ask, format_response
from generation.memory import create_memory

memory = create_memory()

# Turn 1
print('--- Turn 1 ---')
r1 = ask('Who are the authors of the green flashes paper?', memory=memory)
print(format_response(r1))

# Turn 2 — follow-up referencing Turn 1
print('\n--- Turn 2 (follow-up) ---')
r2 = ask('Where do they work?', memory=memory)
print(format_response(r2))

# Turn 3 — another follow-up
print('\n--- Turn 3 (follow-up) ---')
r3 = ask('What did they study?', memory=memory)
print(format_response(r3))
