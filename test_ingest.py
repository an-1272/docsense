from ingestion import ingest

n = ingest("demo_corpus/sample.pdf")
print(f'Done — ingested {n} chunks')