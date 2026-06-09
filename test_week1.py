from ingestion import ingest
from retrieval.search import search

# Step 1: ingest a document
n = ingest("demo_corpus/sample.pdf")
print(f'Ingested {n} chunks')

# Step 2: query it
query = "When are Lightning flashes frequently observable?"
results = search(query, n_results=5)

print(f'\nTop {len(results)} results for: "{query}"\n')
for i, r in enumerate(results, 1):
    print(f'--- Result {i} (page {r["page"]}, distance: {r["distance"]:.4f}) ---')
    print(r['text'][:300])
    print()
