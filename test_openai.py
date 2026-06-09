from openai import OpenAI
from dotenv import load_dotenv
from generation.prompts import SYSTEM_PROMPT

load_dotenv()
client = OpenAI()

response = client.chat.completions.create(
    model='gpt-4o-mini',
    max_tokens=1024,
    messages=[
        {'role': 'system', 'content': SYSTEM_PROMPT},
        {'role': 'user', 'content': 'When can lightning flashes be observed?'}
    ]
)
print(response.choices[0].message.content)
