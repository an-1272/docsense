from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

MAX_TOKEN_LIMIT = 1000

class SimpleSummaryMemory:
    """
    Lightweight summary buffer memory.
    Keeps last 4 turns verbatim, summarises older ones.
    """
    def __init__(self):
        self.recent_turns = []
        self.summary = ""
        self._llm = None  # deferred — not created until first use

    @property
    def llm(self):
        if self._llm is None:
            self._llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
        return self._llm
    
    def add_turn(self, query: str, answer: str):
        self.recent_turns.append({'user': query, 'assistant': answer})
        if len(self.recent_turns) > 4:
            oldest = self.recent_turns.pop(0)
            self._summarise(oldest)

    def _summarise(self, turn: dict):
        prompt = (
            f"Existing summary: {self.summary}\n\n"
            f"New exchange to add:\n"
            f"User: {turn['user']}\n"
            f"Assistant: {turn['assistant']}\n\n"
            f"Update the summary to include this exchange concisely."
        )
        response = self.llm.invoke(prompt)
        self.summary = response.content

    def get_history_string(self) -> str:
        parts = []
        if self.summary:
            parts.append(f"[Earlier conversation summary]: {self.summary}")
        for turn in self.recent_turns:
            parts.append(f"User: {turn['user']}")
            parts.append(f"Assistant: {turn['assistant']}")
        return "\n".join(parts)


def create_memory() -> SimpleSummaryMemory:
    return SimpleSummaryMemory()

def add_turn(memory: SimpleSummaryMemory, query: str, answer: str):
    memory.add_turn(query, answer)

def get_history_string(memory: SimpleSummaryMemory) -> str:
    return memory.get_history_string()

def rewrite_query(query: str, memory, llm=None) -> str:
    """
    Rewrite a follow-up query into a self-contained search query
    using conversation history as context.
    """
    history = memory.get_history_string()
    if not history:
        return query

    rewriter = llm or ChatOpenAI(model='gpt-4o-mini', temperature=0)
    prompt = (
        f"Given this conversation history:\n{history}\n\n"
        f"Rewrite this follow-up question as a complete, self-contained "
        f"search query that includes all necessary context from the history.\n"
        f"Follow-up question: {query}\n\n"
        f"Rewritten query (one sentence, no explanation):"
    )
    response = rewriter.invoke(prompt)
    rewritten = response.content.strip()
    return rewritten