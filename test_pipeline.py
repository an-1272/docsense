from pipeline import ask, format_response

# Test 1: question that IS in the document
result = ask('When can lightning flashes be observed?')
#result = ask('What is the capital of France?')
print(format_response(result))

