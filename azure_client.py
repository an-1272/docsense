# azure_client.py
# Single place that decides OpenAI vs Azure OpenAI for every client in the
# project (chat + embeddings), so USE_AZURE is checked once instead of
# duplicated across generator.py, critique.py, memory.py, title_chunk.py,
# pinecone_embedder.py, pinecone_search.py, and eval/run_eval.py.
import os
from openai import OpenAI, AzureOpenAI
from dotenv import load_dotenv

load_dotenv()

USE_AZURE = os.getenv('USE_AZURE', 'false').lower() == 'true'

AZURE_API_VERSION = '2024-02-15-preview'

CHAT_MODEL = (
    os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4o-mini')
    if USE_AZURE else 'gpt-4o-mini'
)
EMBEDDING_MODEL = (
    os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')
    if USE_AZURE else 'text-embedding-3-small'
)


def get_openai_client():
    """Returns an AzureOpenAI client when USE_AZURE=true, else a plain OpenAI client.
    Same .chat.completions.create() / .embeddings.create() surface either way —
    callers just need to pass CHAT_MODEL / EMBEDDING_MODEL instead of a hardcoded name."""
    if USE_AZURE:
        return AzureOpenAI(
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            api_version=AZURE_API_VERSION,
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
        )
    return OpenAI()


def get_chat_llm(temperature: float = 0):
    """LangChain chat model for the two LangChain-native call sites in
    generation/memory.py (SimpleSummaryMemory's summariser + rewrite_query)."""
    if USE_AZURE:
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_deployment=os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME'),
            api_version=AZURE_API_VERSION,
            azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key=os.getenv('AZURE_OPENAI_API_KEY'),
            temperature=temperature,
        )
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model='gpt-4o-mini', temperature=temperature)
