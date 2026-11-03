from ingestion import ingest

n1 = ingest('eval/corpus/sample.pdf', source_name='demo_corpus/sample.pdf')
n2 = ingest('eval/corpus/sample2.pdf', source_name='demo_corpus/sample2.pdf')
print(f'Total chunks ingested: {n1 + n2}')

