def build_context(chunks: list[dict]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source = chunk['source'].replace('\\', '/').split('/')[-1]  # just filename
        context_parts.append(
            f'[Source: {source} | Page {chunk["page"]}]\n'
            f'{chunk["text"]}\n'
        )
    return '\n'.join(context_parts)