from app.vectorstore.store import get_vector_store

store = get_vector_store("ledger_chunks")
query = "What was JPMorgan Chase's net income for fiscal year 2023?"
entity_filter = {"company": {"$in": ["JPMorgan"]}, "fiscal_year": {"$in": ["FY2023"]}}
results = store.similarity_search_with_score(query, k=5, filter=entity_filter)

for i, (doc, score) in enumerate(results, 1):
    print(f"#{i} is_table={doc.metadata.get('is_table')!r} section={doc.metadata.get('section')!r}")
    print(f"   content={doc.page_content!r}")
