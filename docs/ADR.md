# DocSense — Architecture Decision Record

Each entry: the context, the decision, what it cost, and the evidence behind it.
Status values: **Accepted** (in production code and measured), **Accepted — pending live validation** (code written and structurally verified, not yet run against the real service).

---

## ADR-001 — LangChain linear chain → LangGraph state machine (Reflection pattern)

**Status:** Accepted · commit `d6d6a2f` · 2026-09-13

**Context.** The original pipeline was a fixed chain: retrieve → rerank → generate. If retrieval came back weak, the only outcome was a low-confidence fallback. There was no way to notice a bad retrieval and try again.

**Decision.** Rebuild `ask()` as a LangGraph `StateGraph`: `retrieve → critique → revise → respond`. An LLM critique judges whether the retrieved chunks can actually answer the question. If not, the query is reformulated and retrieval retried, capped at `MAX_RETRIES = 2`. The external `ask()` signature didn't change, so the UI and eval harness needed no changes.

**Why a graph, not more chain code.** The conditional loop (critique → revise → retrieve) is explicit and inspectable. `compiled_graph.stream()` gives a node-by-node trace, which is how the bug below was found.

**Consequences / lesson.** The first version made answers *worse* on some questions. A trace showed a retrieval scoring 0.87 relevance whose critique even *named the correct answer*, yet judged it "insufficient". The reformulated query then retrieved the wrong document (0.106), which critique approved. Fix: `should_critique()` skips critique when retrieval already clears the same HIGH-confidence bar the generator uses (relevance > 0.5). Reflection now only runs on borderline retrievals. An LLM judge shouldn't get to overrule a strong deterministic signal.

**Measured.** Faithfulness 0.79 / answer relevancy 0.80, against a 0.80 / 0.73 baseline (15-question LLM-as-judge set, scoped to its original corpus).

---

## ADR-002 — Reflection over ReAct

**Status:** Accepted · 2026-09-13

**Context.** Both are standard agent patterns. ReAct lets the model choose among tools in an open loop. Reflection runs a fixed workflow and lets the model judge and correct its own intermediate output.

**Decision.** Reflection.

**Rationale.**
- **There is one tool.** DocSense only ever retrieves from its own index. ReAct's value is choosing between tools; with one tool, that's an extra LLM call per step that buys nothing.
- **Bounded cost and latency.** Worst case is fixed: 1 + 2 retries = 3 retrievals and 3 rerank calls. That matters on Cohere's free tier (10 calls/min). The revise node also sleeps 2 s between retries so a single question can't burst past the limit.
- **Evaluable.** A fixed graph produces comparable traces across eval runs. An open ReAct loop varies its path run to run, which makes regressions harder to attribute.

**Revisit when** a second tool exists (web search, SQL over structured data, a calculator). That's the point where tool choice becomes a real decision.

---

## ADR-003 — Two-stage retrieval: bi-encoder top-20 → Cohere cross-encoder top-5

**Status:** Accepted

**Context.** Embedding similarity is fast but imprecise. It compares two independently computed vectors.

**Decision.** Over-fetch 20 candidates by vector similarity, then re-rank with Cohere `rerank-english-v3.0`, which reads query and chunk *jointly*, and keep the top 5.

**Consequences.** One extra API call per query. Confidence logic has to handle two opposite scales: Chroma distance (lower = better) and Cohere relevance (higher = better). An earlier bug came from treating them as one scale, so `generator.py` branches on the presence of `relevance_score` and that branching is deliberately left in place. An A/B toggle in the UI makes the quality difference demonstrable.

---

## ADR-004 — 400-character chunks

**Status:** Accepted

**Context.** Started at 1000 characters. Chunks spanning several ideas produced "blurry" averaged embeddings that matched nothing strongly (semantic dilution).

**Decision.** 400 characters, one idea per chunk. Overlap is the tunable knob: it was raised 80 → 160 after two eval failures traced to facts split across chunk boundaries, without touching chunk size or thresholds.

---

## ADR-005 — Conservative grounding: keep the 0.1 relevance fallback threshold

**Status:** Accepted

**Context.** Three eval questions fail because their best chunk scores just under the 0.1 relevance cutoff, so the system falls back to "not found".

**Decision.** Keep the threshold. Lowering it to pass those three would also let through low-relevance chunks on out-of-scope questions, which is where hallucinations come from. For a document-grounded assistant, a false "I couldn't find that" is cheaper than a confident wrong answer.

---

## ADR-006 — Document scoping: picker first, deterministic auto-detection second

**Status:** Accepted · 2026-09-12 (picker), 2026-11-03 (auto-detection)

**Context.** With several documents in one shared index, "what does the HR2020 doc say?" searched everything, because nothing used the filename metadata stored on each chunk.

**Decision.**
1. A per-document **title/summary chunk** at ingest time gives each document an identity that queries can match. It is written as **one prose sentence**, not labelled metadata: the cross-encoder reranker scored the original `Title: / Summary:` format 0.001 for "What is the main topic of the paper?" (the question it existed for) versus 0.92+ for prose. Wording was chosen by measured rerank score across phrasings. Eval moved 0.80/0.73 → **0.83/0.87** (2026-11-03).
2. A sidebar **multi-select scope picker** passes an explicit `source_filter`.
3. **Query-time filename detection** (`retrieval/scope_detect.py`) applies when the picker is empty. It is regex-based, **not an LLM call**: it runs on every question, so it has to be free, instant and predictable. A wrong auto-scope silently hides the correct document from retrieval, which is worse than not scoping, so it only fires on unambiguous signals: a full filename, a distinctive stem (`HR2020`, `biology-11-00233`), or a plain stem followed by a document noun ("the sample doc"). The applied scope is shown under the answer.

**Related lesson.** Eval scores dropped from 0.80/0.73 to ~0.6 with no code changes. The cause was new documents added to the shared index after the benchmark was written, so the harness was unknowingly searching three unrelated PDFs. The harness now pins `source_filter` to its own corpus. **A benchmark is only valid for the corpus it was measured against.**

---

## ADR-007 — OpenAI API → Azure OpenAI Service (behind a flag)

**Status:** Accepted — pending live validation · commit `dec5a3b`

**Context.** Enterprise deployments typically need model traffic to stay inside their cloud tenancy: data residency, private networking, Entra ID / RBAC instead of a shared API key, and Azure's content-filtering and audit tooling.

**Decision.** Route every model call through one factory, `azure_client.py` (`get_openai_client()`, `get_chat_llm()`, `CHAT_MODEL`, `EMBEDDING_MODEL`). It returns an Azure client when `USE_AZURE=true`, otherwise plain OpenAI. All 8 call sites import from it. Same models (`gpt-4o-mini`, `text-embedding-3-small`), so embeddings stay compatible with the existing index.

**Why a factory, not if/else at each call site.** One place to get the Azure-specific details right (endpoint, API version, deployment names vs model names), and one place a future model or API-version bump has to touch.

**Trade-offs.** Azure OpenAI needs access approval and per-model *deployments*. New models arrive on Azure later than on OpenAI. The flag keeps the OpenAI path as the working default until Azure is validated.

---

## ADR-008 — Pinecone → Azure AI Search (behind a flag)

**Status:** Accepted · **live since 2026-11-03** · code `dec5a3b`, fixes + cutover `4b82f2d`

**Context.** Pinecone is pure vector search, and it's an external vendor outside the Azure tenancy.

**Decision.** Add Azure AI Search as a third retrieval backend (`USE_AZURE_SEARCH`, checked before `USE_PINECONE`). It uses the same chunk shape, return shape and `source_filter` mechanism, and Cohere reranking stays on top.

**Rationale.**
- **Hybrid search.** Vector and BM25 keyword retrieval in one query. Pure embeddings are weak on exact tokens (IDs, codes, filenames, acronyms), which is the failure class ADR-006 had to work around.
- **Single cloud.** The vector store sits in the same tenancy, network and RBAC model as the model endpoint.

**Detail.** The filter uses `search.in(source, ..., '|')` rather than a `,` delimiter, so a filename containing a comma can't break scoping.

**Trade-offs.** Paid tiers cost more than Pinecone's free tier (the demo runs on the Free tier: 50 MB, 3 indexes), and the index schema must be defined explicitly up front; it lives in code at `deploy/create_search_index.py`.

**Validation before cutover (2026-11-03).** The first real run found three bugs in the never-executed code: document keys built from file paths are invalid Azure keys (now base64url), apostrophes broke the OData filter (now escaped), and `ingest()` never routed to Azure Search, so uploads would have gone to Pinecone while retrieval read an empty index. After the fixes, the eval harness on Azure scored faithfulness 0.83 / relevancy 0.84 against Pinecone's 0.83 / 0.87; the only delta is a known judge-rubric quirk on a correctly refused question. Pinecone stays populated as a one-flag rollback.

---

## ADR-009 — Hosting on Azure Container Apps

**Status:** Accepted · 2026-11-03

**Context.** The app already ships as a Docker image. It's a portfolio demo with bursty, low traffic.

**Decision.** Azure Container Apps.

**Rationale.**
- Runs the existing Dockerfile unchanged. No platform-specific rewrite, unlike App Service code deploys or Functions.
- **Scale to zero.** Near-zero cost while idle. The trade-off is a cold start on the first visit.
- Managed HTTPS ingress with WebSocket support, which Streamlit requires.
- Secrets are stored in the Container App and injected as env vars. API keys are never baked into the image.
- AKS would be heavy over-provisioning for a single container.

**Known limitation.** SQLite session history (`db/sessions.db`) lives on the container's ephemeral filesystem, so it resets on restart or scale-to-zero. That's acceptable for a demo. The production fix is an Azure Files volume mount, or moving sessions to a managed store.
