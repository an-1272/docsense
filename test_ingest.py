from ingestion import ingest

n = ingest("eval/corpus/sample.pdf", source_name="demo_corpus/sample.pdf")
print(f'Done — ingested {n} chunks')