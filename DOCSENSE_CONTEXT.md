# DocSense — Full Project Context for Claude Code

## What This Project Is
DocSense is a production-pattern RAG (Retrieval-Augmented Generation) application built as an AI Engineering portfolio project by Angelina Raju. Users upload PDF documents and receive cited, grounded answers to natural language questions. Every answer traces back to the source document with page references.

**Owner:** Angelina Raju — SOC Analyst at Paramount Computer Systems, Dubai. Transitioning into Agentic AI Engineering roles. Targeting relocation to Bangalore. Holds CEH, pursuing AZ-500 and AI-102.

**GitHub:** https://github.com/an-1272/docsense

---

## Build History — What Was Built and When

### Week 1 — Ingestion Pipeline
- PDF parser (PyMuPDF) returning list of {page, text, source}
- Chunker (LangChain RecursiveCharacterTextSplitter) — started at 1000 chars, reduced to 400 chars after discovering semantic dilution
- Embedder (OpenAI text-embedding-3-small, 1536 dims) into ChromaDB
- Similarity search returning top-k chunks with distance scores
- Checkpoint: given a query, returns 5 most relevant chunks

### Week 2 — Retrieval + Generation
- LangChain retrieval chain wired to OpenAI GPT-4o-mini
- System prompt engineered for grounding, citation, fallback
- Citation format: [Source: filename | Page X]
- Confidence scoring: distance < 0.30 = HIGH, < 0.45 = MEDIUM, else LOW
- Fallback: fires when confidence below threshold
- Multi-document support
- Checkpoint: grounded cited answers with fallback for out-of-scope questions

### Week 3 — Streamlit UI
- File upload panel with progress indicator
- Chat interface with streaming
- Citation panel showing source and page per answer
- Confidence badge (🟢🟡🔴)
- Demo mode loading pre-ingested corpus
- Clear conversation button
- Context limit warning after 16+ messages
- Error handling — graceful API failure messages

### Add-On 1 — Cohere Re-ranking
- Two-stage retrieval: bi-encoder (top-20) → Cohere rerank-english-v3.0 (top-5)
- A/B toggle in sidebar — re-ranking on/off
- Mode label under each answer (🔄 Re-ranked / 🔍 Similarity only)
- Confidence scoring updated for Cohere relevance scores (opposite scale to ChromaDB)
- System prompt rewritten for conversational synthesis (not just passage retrieval)

### Add-On 2 — Conversation Memory
- SimpleSummaryMemory — custom class (LangChain memory module deprecated/moved)
- Keeps last 4 turns verbatim, summarises older turns using GPT-4o-mini
- SQLite session persistence (db/sessions.py) — survives page refreshes
- Query rewriting — follow-up questions expanded using history before retrieval
- Clear conversation resets UI state, memory buffer, and SQLite session

### Project 1 Week 1 — Docker + Pinecone
- Dockerfile and docker-compose.yml — app runs with docker-compose up
- Pinecone migration — USE_PINECONE env flag routes between ChromaDB and Pinecone
- ingestion/pinecone_embedder.py — batched upsert to Pinecone
- retrieval/pinecone_search.py — Pinecone query + Cohere rerank
- pipeline.py updated to route based on USE_PINECONE

### Project 1 Week 2 — GitHub Actions + LangSmith + Eval
- GitHub Actions CI — .github/workflows/ci.yml — lint + pytest on every push to main
- 5 unit tests in tests/test_pipeline.py (no API calls)
- LangSmith tracing — @traceable on ask() and generate_answer()
- LLM-as-judge evaluation harness (eval/run_eval.py) — GPT-4o-mini scores faithfulness + relevancy
- 15 test questions in eval/eval_dataset.py (12 in-scope, 3 out-of-scope)
- time.sleep(7) added between questions to handle Cohere free tier rate limit

---

## Current Status
- ✅ Week 1 — Ingestion pipeline
- ✅ Week 2 — Retrieval + generation
- ✅ Week 3 — Streamlit UI
- ✅ Add-On 1 — Cohere re-ranking with A/B toggle
- ✅ Add-On 2 — Conversation memory + query rewriting + SQLite
- ✅ Project 1 Week 1 — Docker + Pinecone
- ✅ Project 1 Week 2 — GitHub Actions + LangSmith
- 🔄 Project 1 Week 2 — Eval harness (built, needs final run to completion)
- ⏳ Project 2 — LangGraph + Azure (NOT STARTED)

---

## Troubleshooting History — All Issues Resolved

### Session 1 — Re-ranking Add-On
**Issue 1: Confidence threshold mismatch**
ChromaDB distance scores (lower=better, threshold 0.45) vs Cohere relevance scores (higher=better, threshold 0.1) are opposite scales. The same threshold was applied to both, causing high-quality re-ranked results to incorrectly trigger the fallback.
Fix: Added score-type detection in generator.py — checks for 'relevance_score' key in chunk dict and applies correct threshold for each system.

**Issue 2: LLM firing fallback on indirect evidence**
System prompt was too strict — "Answer ONLY from context" caused GPT-4o-mini to fire fallback when chunks had partial/indirect evidence rather than word-for-word matching.
Fix: Rewrote system prompt to explicitly permit synthesis across passages while keeping the grounding boundary. Fallback only fires when NO relevant information exists.

**Issue 3: Polluted database from duplicate ingestion**
Same document ingested via terminal AND Streamlit uploader created duplicate chunks under different source paths. ChromaDB upsert deduplicates by chunk_id which is built from the source path — so same content under two paths = two sets of chunks. Caused weak distance scores (0.48+).
Fix: Deleted db/, reduced chunk size from 1000 to 400, re-ingested via terminal only. Established rule: never mix terminal and UI ingestion for same document.

**Issue 4: PowerShell vs Command Prompt command differences**
rmdir /s /q fails in PowerShell. Use Remove-Item -Recurse -Force.
type nul > file.py fails in PowerShell. Use New-Item file.py.

### Session 2 — Conversation Memory
**Issue 1: Bot behaving like a search engine**
Root cause: system prompt was a citation machine, not a conversational guide. GPT-4o-mini defaulted to safest behaviour — repeating passages — rather than synthesising.
Fix: Complete system prompt rewrite with conversational philosophy, tone guidance, and explicit permission to reason across passages.

**Issue 2: LangChain memory module not found**
LangChain moved ConversationSummaryBufferMemory to langchain_community, then restructured again. Import path kept changing.
Fix: Replaced LangChain dependency entirely with custom SimpleSummaryMemory class — same pattern, zero LangChain dependency, more stable.

**Issue 3: Follow-up questions returning fallback**
Memory was passing history to LLM correctly but retrieval was still stateless. "Where do they work?" contains no keywords matching document chunks.
Fix: Query rewriting step added before retrieval — rewrites follow-up questions into self-contained queries using conversation history. "Where do they work?" → "Where does Gilbert Green work?"

**Issue 4: rewrite_query not found despite being in file**
VS Code did not save the file correctly after pasting — the editor showed the content but disk had the old version.
Fix: Verified with python -c "import generation.memory as m; print(dir(m))" — rewrite_query was absent. Selected all in VS Code, deleted, re-pasted, saved with Ctrl+S.

**Issue 5: Terminal run command pasted into Python file**
python test_memory.py accidentally pasted into test_memory.py itself, causing SyntaxError.
Fix: Opened file, deleted the shell command line, re-saved.

**Issue 6: Duplicate sidebar block in app.py**
Week 3 placeholder sidebar was never removed when full implementation was added. Both blocks executed, producing duplicate headers.
Fix: Removed placeholder block. Moved confidence_badge() helper above layout so it's defined before use.

### Session 3 — UI Testing + Performance
**Issue 1: Citations showing "Passage 1" instead of filename**
context.py labelled chunks as "[Passage 1 | Source: ...]" — LLM adopted this label despite system prompt saying otherwise. Context format overrides system prompt for citation style.
Fix: Updated build_context() to label passages as "[Source: filename | Page X]" directly.

**Issue 2: Temp file paths in citations**
Streamlit uploader writes to Windows temp directory. ingest() was storing this temp path as source metadata in ChromaDB permanently.
Fix: Added source_name parameter to ingest(). app.py passes original filename: ingest(tmp_path, source_name=f"uploads/{uploaded_file.name}").

**Issue 3: Missing db/sessions.py**
File was planned in build document but never created. App showed ModuleNotFoundError on startup.
Fix: Created db/sessions.py with full SQLite implementation and db/__init__.py.

**Issue 4: App taking ~60 seconds to load**
Two compounding causes:
(1) SimpleSummaryMemory.__init__() called ChatOpenAI() on creation — network connection on every Streamlit rerun
(2) Pipeline import chain (cohere, openai, chromadb, langchain) re-ran on every rerun (~2.5s each time)
Fix: (1) Lazy LLM init — @property that creates ChatOpenAI only on first use. (2) @st.cache_resource wrappers for pipeline imports — only runs once per server process.
Result: cold start ~5s, subsequent reruns 0.01–0.05s.

**Issue 5: "Running load_pipeline()" shown during startup**
Streamlit's default cache spinner shows function name.
Fix: show_spinner=False on decorators + with st.spinner('Starting DocSense...') wrapper. Both must be used together.

---

## Project Structure
```
docsense/
  ingestion/
    __init__.py              # Routes to Pinecone or ChromaDB via USE_PINECONE
    parser.py                # PyMuPDF parser
    chunker.py               # 400 chars, 80 overlap
    embedder.py              # ChromaDB (local dev)
    pinecone_embedder.py     # Pinecone (production)
  retrieval/
    __init__.py
    search.py                # ChromaDB + Cohere rerank
    pinecone_search.py       # Pinecone + Cohere rerank
  generation/
    __init__.py
    prompts.py               # System prompt — DO NOT MODIFY without discussion
    context.py               # Formats chunks as [Source: file | Page X]
    generator.py             # GPT-4o-mini + @traceable + confidence scoring
    memory.py                # SimpleSummaryMemory + rewrite_query
  db/
    __init__.py
    sessions.py              # SQLite session persistence
  eval/
    __init__.py
    eval_dataset.py          # 15 test questions + ground truth
    run_eval.py              # LLM-as-judge scoring (run with python -m eval.run_eval)
  tests/
    test_pipeline.py         # 5 unit tests, no API calls
  .github/
    workflows/
      ci.yml                 # GitHub Actions — lint + pytest
  app.py                     # Streamlit frontend
  pipeline.py                # ask() + format_response() + @traceable
  Dockerfile
  docker-compose.yml
  requirements.txt
  CLAUDE.md                  # This file
```

---

## Tech Stack
| Layer | Technology | Notes |
|---|---|---|
| Parsing | PyMuPDF (fitz) | Page-level metadata |
| Chunking | LangChain RecursiveCharacterTextSplitter | 400 chars, 80 overlap |
| Embeddings | OpenAI text-embedding-3-small | 1536 dims |
| Vector Store prod | Pinecone | Index: docsense |
| Vector Store dev | ChromaDB | Stored in db/ |
| Re-ranking | Cohere rerank-english-v3.0 | Top-20 → top-5 |
| Generation | OpenAI GPT-4o-mini | Grounded answers |
| Memory | SimpleSummaryMemory (custom) | Last 4 turns + summary |
| Sessions | SQLite | db/sessions.db |
| Frontend | Streamlit | Chat + citations + sidebar |
| Container | Docker + docker-compose | |
| CI/CD | GitHub Actions | Push to main triggers run |
| Observability | LangSmith | smith.langchain.com project: docsense |
| Evaluation | LLM-as-judge | GPT-4o-mini scorer |

---

## Environment Variables (.env)
```
OPENAI_API_KEY=...
COHERE_API_KEY=...
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=docsense
USE_PINECONE=true
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=docsense
```
Note: LANGSMITH uses LANGSMITH_ prefix NOT LANGCHAIN_. No V2 suffix.

---

## Key Architectural Decisions

### Two-Stage Retrieval
Bi-encoder (similarity search, top-20) → cross-encoder (Cohere rerank, top-5).
Bi-encoders are fast but imprecise — semantic dilution in large chunks.
Cross-encoders read query and chunk jointly — precision scores.
A/B toggle in UI demonstrates quality difference.

### Chunk Size — 400 Characters
Started at 1000 chars. Semantic dilution discovered — chunks with multiple ideas produce blurry average embeddings.
Reduced to 400 chars with 80-char overlap. One idea per chunk = precise embeddings.
DO NOT CHANGE without discussion.

### Confidence Scoring — Opposite Scales
ChromaDB: distance (lower=better), threshold 0.45. MEDIUM if < 0.45, LOW if >= 0.45.
Cohere: relevance (higher=better), threshold 0.1. LOW if < 0.1.
HIGH confidence: distance < 0.30 OR relevance > 0.5.
generator.py detects score type via 'relevance_score' key in chunk dict.
DO NOT simplify this logic — it was a real production bug.

### Query Rewriting
Before searching ChromaDB/Pinecone, follow-up questions are rewritten.
rewrite_query() in memory.py uses GPT-4o-mini + conversation history.
search_query used for retrieval; original query used for generation.
Empty history = original query returned unchanged.

### System Prompt — Conversational Grounded Assistant
DO NOT revert to citation-machine style. The current prompt:
- Permits synthesis across passages
- Permits elaboration within document evidence
- Uses natural conversational fallback (not rigid phrase)
- Cites on factual claims, not every sentence
- Matches user's register (casual/technical)
- Never uses outside knowledge

### Lazy LLM Init
SimpleSummaryMemory._llm is None on init. @property self.llm creates ChatOpenAI on first use.
This prevents OpenAI connection on every Streamlit rerun.

### Source Naming
Terminal: real path used as source.
UI upload: ingest(tmp_path, source_name=f"uploads/{filename}").
Demo: ingest(path, source_name=f"demo_corpus/{filename}").
Never mix terminal and UI ingestion for same document.

---

## Conversation Memory Architecture
```
SimpleSummaryMemory:
  recent_turns: list[dict]   — last 4 turns as {user, assistant}
  summary: str               — compressed older turns
  _llm: None                 — lazy init, ChatOpenAI created on first summarisation

add_turn(memory, query, answer)     — adds turn, pops oldest if >4, summarises it
get_history_string(memory)          — returns formatted history string for LLM
rewrite_query(query, memory)        — expands follow-up using history before retrieval
create_memory()                     — returns fresh SimpleSummaryMemory instance
```

---

## Evaluation Details
Run with: `python -m eval.run_eval` (NOT python eval\run_eval.py)
15 questions: 12 in-scope (green flashes paper) + 3 out-of-scope (should return fallback)
Scores: faithfulness (claims grounded in context) + answer_relevancy (answers the question)
Target: faithfulness > 0.80, answer_relevancy > 0.70
time.sleep(7) between questions — Cohere free tier: 10 API calls/minute
Results saved to eval/results_TIMESTAMP.json

---

## Project 2 — LangGraph + Azure (FULL SPEC)

### Components

**1. LangGraph State Machine — Reflection Pattern**
Rebuild pipeline.py ask() as a LangGraph graph.
Nodes: retrieve → critique → revise → respond
- retrieve: Pinecone/Azure AI Search query + Cohere rerank
- critique: LLM evaluates if retrieved chunks are sufficient to answer
- revise: if critique fails, reformulate query and retrieve again (max 2 retries)
- respond: generate final grounded cited answer
This is the Reflection agent pattern — explicitly nameable in interviews.

**2. Azure OpenAI Service**
Replace openai SDK calls with Azure OpenAI endpoint.
Same models (GPT-4o-mini, text-embedding-3-small) hosted on Azure.
Required for AI-102 certification alignment and enterprise compliance.
Config via USE_AZURE env flag — same pattern as USE_PINECONE.

**3. Azure AI Search**
Replace Pinecone with Azure's managed hybrid search.
Supports vector + keyword search simultaneously.
Keeps full stack within Azure — no external vector DB.
Config via USE_AZURE_SEARCH env flag.

**4. Azure Container Apps**
Deploy Dockerised app to Azure serverless container platform.
Scales to zero when not in use.
GitHub Actions deploys on push to main.
Gives live public URL for resume and interviews.

**5. Architecture Decision Record (ADR)**
Short document (1-2 pages) explaining every major technical choice:
- Why Pinecone → Azure AI Search
- Why OpenAI API → Azure OpenAI Service
- Why LangChain chains → LangGraph state machine
- Why Reflection pattern over ReAct
Standard engineering practice — signals maturity to interviewers.

### Environment Variables for Project 2
```
USE_AZURE=true
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_SEARCH_ENDPOINT=...
AZURE_SEARCH_KEY=...
AZURE_SEARCH_INDEX=docsense
USE_AZURE_SEARCH=true
```

---

## Important Rules for Claude Code
1. Always run from project root: C:\Users\Angelina Raju\docsense
2. Always activate venv: venv\Scripts\activate
3. PowerShell: use Remove-Item -Recurse -Force (not rmdir /s /q)
4. PowerShell: use New-Item filename.py (not type nul >)
5. Paths with spaces need quotes: cd "C:\Users\Angelina Raju\docsense"
6. Run eval with python -m eval.run_eval (not python eval\run_eval.py)
7. DO NOT change chunk size (currently 400 chars, 80 overlap)
8. DO NOT change system prompt without explicit instruction
9. DO NOT simplify confidence threshold logic — opposite scales are intentional
10. DO NOT mix terminal and UI ingestion for same document
11. test_pipeline.py in root = integration test (needs API keys)
12. tests/test_pipeline.py = unit tests (no API calls, runs in CI)
13. LangSmith env vars use LANGSMITH_ prefix, NOT LANGCHAIN_ — no V2 suffix
14. Cohere free tier: 10 calls/minute — add time.sleep(7) in any batch eval loops

---

## Common Commands
```bash
# Activate venv (always do this first)
venv\Scripts\activate

# Start app locally
streamlit run app.py

# Start app in Docker
docker-compose up

# Ingest document
python test_ingest.py

# Run pipeline test (integration — needs API keys)
python test_pipeline.py

# Run A/B rerank test
python test_rerank_ab.py

# Run memory test
python test_memory.py

# Run evaluation harness
python -m eval.run_eval

# Run unit tests (no API keys needed)
pytest tests/ -v

# Commit and push
git add .
git commit -m "message"
git push

# Update requirements after pip installs
pip freeze > requirements.txt
```

---

## Resume Entry (Current — as of Project 1 completion)
**DocSense — Production-Pattern RAG System**
Python · OpenAI · Cohere Rerank · Pinecone · LangChain · LangSmith · Docker · GitHub Actions · SQLite · Streamlit

- Built production-pattern RAG pipeline: two-stage retrieval (OpenAI embeddings + Cohere Rerank cross-encoder), GPT-4o-mini generation, confidence-based fallback eliminating out-of-scope hallucinations
- Diagnosed and resolved retrieval quality issues through systematic debug instrumentation: semantic dilution from large chunk sizes; scoring mismatch between ChromaDB distance scores and Cohere relevance scores operating on opposite scales
- Implemented A/B retrieval toggle with documented before/after quality improvements across three query types — demonstrating measurable impact of re-ranking
- Applied iterative prompt engineering to shift from search-engine behaviour to grounded conversational synthesis — refined against observed failure modes including over-refusal on indirect evidence
- Integrated conversation memory (SimpleSummaryMemory with SQLite persistence) and query rewriting for context-aware multi-turn retrieval
- Containerised with Docker; CI/CD via GitHub Actions (automated tests on every push); LangSmith tracing for end-to-end observability
- LLM-as-judge evaluation harness scoring faithfulness and answer relevancy across 15-question fixed test set
- In Progress: LangGraph reflection agent rewrite with Azure OpenAI and Azure AI Search migration
