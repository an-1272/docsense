from ingestion import ingest

n1 = ingest('demo_corpus/sample.pdf')
n2 = ingest('demo_corpus/sample2.pdf')
print(f'Total chunks ingested: {n1 + n2}')

