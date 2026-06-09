from pipeline import ask, format_response

# Ask something specific to document 1
r1 = ask('When can lightning flashes be observed?')
print('--- Query 1 ---')
print(format_response(r1))

# Ask something specific to document 2
r2 = ask('What are galaxies?')
print('\n--- Query 2 ---')
print(format_response(r2))

