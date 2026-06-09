def build_context(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a context string for the LLM.
    Each chunk is labelled with its source and page number.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f'[Passage {i} | Source: {chunk["source"]} | Page {chunk["page"]}]\n'
            f'{chunk["text"]}\n'
        )
    return '\n'.join(context_parts)
